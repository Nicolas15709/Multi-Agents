"""
AgentExecutor: Real LLM execution layer using Claude + tool use.

Each task is executed by a Claude model that has access to:
  - create_file  / read_file / list_files  — workspace file I/O
  - execute_bash                            — sandboxed shell execution
  - write_output                            — signals task completion

Execution is non-blocking: a daemon thread runs the LLM loop while the
tick-based task_runner checks progress on each tick via the _exec_status
flag stored inside task["details"].
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("agent_executor")

# ─── Constants ────────────────────────────────────────────────────────────────

# Sandbox: literal strings that are always blocked
_COMMAND_BLOCKLIST = frozenset({
    "rm -rf /", "rm -rf ~", ":(){ :|:& };:", "mkfs", "dd if=/dev/zero",
    "chmod -R 777 /", "chown -R", "> /etc/passwd", "curl | sh", "wget | sh",
    "curl | bash", "wget | bash", "shutdown", "reboot", "halt", "poweroff",
    "kill -9 1", "killall", "> /dev/sda", "format c:", "del /f /s /q c:\\",
})

# Sandbox: regex patterns that are always blocked
_COMMAND_BLOCKLIST_PATTERNS = [
    r"rm\s+-rf\s+[/~]",          # rm -rf on root or home
    r">\s*/etc/",                  # overwrite system files
    r"curl.+\|\s*(ba)?sh",        # curl pipe to shell
    r"wget.+\|\s*(ba)?sh",        # wget pipe to shell
    r"python[23]?\s+-c.+exec\(",  # exec via python one-liner
    r"__import__\(.+os",           # Python os import tricks
]


def _set_resource_limits() -> None:
    """Set resource limits for subprocess (Unix only)."""
    import resource  # noqa: PLC0415 — Unix only
    # Max 512 MB virtual memory
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    # Max 100 MB file size
    resource.setrlimit(resource.RLIMIT_FSIZE, (100 * 1024 * 1024, 100 * 1024 * 1024))


@dataclass
class SandboxConfig:
    """Controls what capabilities the sandboxed bash tool grants agents."""
    allow_network: bool = True          # set False to block curl/wget entirely
    allow_git: bool = True              # allow git operations
    allow_package_install: bool = True  # allow pip/npm install
    max_file_size_mb: int = 100
    max_memory_mb: int = 512
    extra_blocked_commands: List[str] = field(default_factory=list)


_PROMPTS_ROOT = Path(__file__).resolve().parent.parent.parent / "prompts"
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent / "workspace"

_AGENT_PROMPT_FILES: Dict[str, str] = {
    "agent-0": "supervisor.AGENTS.md",
    "agent-1": "researcher.AGENTS.md",
    "agent-2": "designer.AGENTS.md",
    "agent-3": "developer.AGENTS.md",
    "agent-4": "qa.AGENTS.md",
}

_DEFAULT_MODEL = "claude-sonnet-4-6"
_MAX_TOOL_ITERATIONS = 12   # Hard cap on agentic loop iterations per task
_BASH_TIMEOUT_SECONDS = 60  # Per-command timeout

# ─── Tool definitions (Claude tool_use format) ────────────────────────────────

_TOOLS: List[Dict] = [
    {
        "name": "create_file",
        "description": (
            "Create or overwrite a file inside the mission workspace. "
            "Use relative paths only. The workspace is isolated per mission."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path, e.g. 'src/app.py'"},
                "content": {"type": "string", "description": "Full file content"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the content of a file in the mission workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files recursively inside the mission workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subdir": {"type": "string", "description": "Optional subdirectory (default: workspace root)"},
            },
        },
    },
    {
        "name": "execute_bash",
        "description": (
            "Execute a shell command in the mission workspace directory. "
            "Returns stdout, stderr, and exit_code. "
            "Use for: running tests, installing packages, git operations, etc. "
            "Timeout per command: 60 seconds."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "write_output",
        "description": (
            "Signal task completion and record the final deliverable. "
            "Call this EXACTLY ONCE when the task is fully done (or blocked). "
            "All created files are automatically registered as artifacts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Concise summary of what was accomplished",
                },
                "status": {
                    "type": "string",
                    "enum": ["done", "blocked"],
                    "description": "'done' = completed, 'blocked' = cannot proceed without human",
                },
                "implementation_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key decisions, assumptions, or next steps",
                },
                "blocker": {
                    "type": "string",
                    "description": "If status=blocked, describe the specific blocker",
                },
            },
            "required": ["summary", "status"],
        },
    },
]


# ─── Workspace helpers ────────────────────────────────────────────────────────

def _workspace(mission_id: str) -> Path:
    ws = _WORKSPACE_ROOT / mission_id
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def _safe_path(workspace: Path, relative: str) -> Path:
    """Resolve a relative path within workspace, blocking path traversal."""
    resolved = (workspace / relative).resolve()
    if not str(resolved).startswith(str(workspace.resolve())):
        raise ValueError(f"Path traversal blocked: {relative!r}")
    return resolved


def _list_workspace_files(workspace: Path) -> List[str]:
    files = []
    for p in workspace.rglob("*"):
        if p.is_file():
            files.append(str(p.relative_to(workspace)))
    return sorted(files)


# ─── Tool executor ────────────────────────────────────────────────────────────

class ToolExecutor:
    def __init__(self, mission_id: str, sandbox: Optional[SandboxConfig] = None):
        self._workspace = _workspace(mission_id)
        self._output_signal: Optional[Dict] = None  # Set when write_output is called
        self._sandbox = sandbox or SandboxConfig()

    @property
    def output_signal(self) -> Optional[Dict]:
        return self._output_signal

    def run(self, tool_name: str, tool_input: Dict) -> str:
        try:
            if tool_name == "create_file":
                return self._create_file(tool_input["path"], tool_input["content"])
            if tool_name == "read_file":
                return self._read_file(tool_input["path"])
            if tool_name == "list_files":
                return self._list_files(tool_input.get("subdir", ""))
            if tool_name == "execute_bash":
                return self._execute_bash(tool_input["command"])
            if tool_name == "write_output":
                return self._write_output(tool_input)
            return f"Unknown tool: {tool_name}"
        except Exception as exc:
            return f"Tool error ({tool_name}): {exc}"

    def _create_file(self, path: str, content: str) -> str:
        target = _safe_path(self._workspace, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"File created: {path} ({len(content)} chars)"

    def _read_file(self, path: str) -> str:
        target = _safe_path(self._workspace, path)
        if not target.exists():
            return f"File not found: {path}"
        return target.read_text(encoding="utf-8")

    def _list_files(self, subdir: str = "") -> str:
        base = _safe_path(self._workspace, subdir) if subdir else self._workspace
        files = _list_workspace_files(base)
        if not files:
            return "Workspace is empty."
        return "\n".join(files)

    def _check_command_safety(self, command: str) -> Optional[str]:
        """Return an error message if the command is blocked, None if safe."""
        sandbox = self._sandbox

        # Network blocking: reject curl/wget when allow_network=False
        if not sandbox.allow_network:
            if re.search(r"\bcurl\b", command, re.IGNORECASE):
                return "BLOCKED: Network access is disabled (curl not permitted)"
            if re.search(r"\bwget\b", command, re.IGNORECASE):
                return "BLOCKED: Network access is disabled (wget not permitted)"

        # Git blocking
        if not sandbox.allow_git:
            if re.search(r"\bgit\b", command, re.IGNORECASE):
                return "BLOCKED: Git operations are disabled"

        # Package install blocking
        if not sandbox.allow_package_install:
            if re.search(r"\bpip[23]?\s+install\b", command, re.IGNORECASE):
                return "BLOCKED: Package installation is disabled (pip)"
            if re.search(r"\bnpm\s+install\b", command, re.IGNORECASE):
                return "BLOCKED: Package installation is disabled (npm)"

        # Literal blocklist
        for blocked in _COMMAND_BLOCKLIST:
            if blocked in command:
                return f"BLOCKED: Command contains prohibited pattern: {blocked!r}"

        # Extra per-instance blocked commands
        for blocked in sandbox.extra_blocked_commands:
            if blocked in command:
                return f"BLOCKED: Command contains prohibited pattern: {blocked!r}"

        # Regex pattern blocklist
        for pattern in _COMMAND_BLOCKLIST_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return f"BLOCKED: Command matches dangerous pattern: {pattern!r}"

        return None

    def _execute_bash(self, command: str) -> str:
        # Safety check before any subprocess is spawned
        block_reason = self._check_command_safety(command)
        if block_reason:
            logger.warning("Sandbox blocked command: %s | reason: %s", command[:120], block_reason)
            return block_reason

        # Apply resource limits on Unix; no-op on Windows
        preexec = _set_resource_limits if sys.platform != "win32" else None

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self._workspace),
                capture_output=True,
                text=True,
                timeout=_BASH_TIMEOUT_SECONDS,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
                preexec_fn=preexec,
            )
            parts = []
            if result.stdout.strip():
                parts.append(f"STDOUT:\n{result.stdout.strip()}")
            if result.stderr.strip():
                parts.append(f"STDERR:\n{result.stderr.strip()}")
            parts.append(f"EXIT CODE: {result.returncode}")
            return "\n".join(parts) if parts else f"EXIT CODE: {result.returncode}"
        except subprocess.TimeoutExpired:
            return f"TIMEOUT: command exceeded {_BASH_TIMEOUT_SECONDS}s"
        except Exception as exc:
            return f"EXECUTION ERROR: {exc}"

    def _write_output(self, tool_input: Dict) -> str:
        self._output_signal = {
            "summary": tool_input.get("summary", ""),
            "status": tool_input.get("status", "done"),
            "implementation_notes": tool_input.get("implementation_notes", []),
            "blocker": tool_input.get("blocker"),
            "artifacts": [
                {"path": f, "type": _guess_type(f), "summary": ""}
                for f in _list_workspace_files(self._workspace)
            ],
        }
        return "Output recorded. Task will be marked complete."


def _guess_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    code_exts = {".py", ".js", ".ts", ".jsx", ".tsx", ".sh", ".go", ".rs", ".java", ".c", ".cpp"}
    doc_exts = {".md", ".txt", ".rst", ".pdf"}
    config_exts = {".json", ".yaml", ".yml", ".toml", ".env", ".ini"}
    if ext in code_exts:
        return "code"
    if ext in doc_exts:
        return "doc"
    if ext in config_exts:
        return "config"
    return "asset"


# ─── System prompt loader ─────────────────────────────────────────────────────

def _load_system_prompt(agent_id: str) -> str:
    prompt_file = _AGENT_PROMPT_FILES.get(agent_id)
    if not prompt_file:
        return f"You are {agent_id}, a specialized AI agent."
    path = _PROMPTS_ROOT / prompt_file
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return f"You are {agent_id}, a specialized AI agent."


# ─── Context builder ──────────────────────────────────────────────────────────

def _build_task_prompt(mission: Dict, task: Dict) -> str:
    details = task.get("details") or {}
    ctx = details.get("coordination_context") or {}
    criteria = details.get("acceptance_criteria") or []
    tools_hint = details.get("tool_primitives") or []
    capabilities = details.get("required_capabilities") or []
    phase = details.get("phase_kind") or "general"
    sequence = details.get("sequence", "?")
    total = details.get("sequence_total", "?")

    lines = [
        f"## Mission",
        f"**Goal:** {mission.get('goal', 'No goal specified')}",
        f"**Mode:** {mission.get('mode', 'general')}",
        f"**Priority:** {mission.get('priority', 'medium')}",
        "",
        f"## Your Task (Step {sequence}/{total} — {phase})",
        f"**Title:** {task.get('title', 'Untitled task')}",
    ]

    if criteria:
        lines += ["", "**Acceptance Criteria:**"]
        lines += [f"- {c}" for c in criteria]

    if capabilities:
        lines += ["", f"**Required Capabilities:** {', '.join(capabilities)}"]

    if tools_hint:
        lines += ["", f"**Available Tool Primitives:** {', '.join(tools_hint)}"]

    # Inject coordination context (previous agent outputs)
    dep_summaries = ctx.get("dependency_summaries") or []
    if dep_summaries:
        lines += ["", "## Context from Previous Agents"]
        for dep in dep_summaries:
            agent = dep.get("agent_id", "?")
            title = dep.get("task_title", "")
            content = dep.get("summary") or dep.get("output") or ""
            if content:
                lines += [f"### {agent} — {title}", content, ""]

    lines += [
        "",
        "## Instructions",
        "1. Use the provided tools to complete this task.",
        "2. Create any necessary files in the workspace.",
        "3. Run tests or validation commands to confirm your work.",
        "4. Call `write_output` exactly once when finished.",
        "5. If you are blocked by something outside your control, call `write_output` with status='blocked'.",
    ]

    return "\n".join(lines)


# ─── Main executor ────────────────────────────────────────────────────────────

class AgentExecutor:
    """
    Runs a single task using Claude with tool use in a blocking loop.
    Designed to be called from a daemon thread by TaskRunner.
    """

    def __init__(self, model: str = _DEFAULT_MODEL, sandbox: Optional[SandboxConfig] = None):
        self._model = model
        self._client = None  # Lazy init
        self._sandbox = sandbox or SandboxConfig()

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic  # noqa: PLC0415
                self._client = anthropic.Anthropic(
                    api_key=os.environ.get("ANTHROPIC_API_KEY", "")
                )
            except ImportError:
                raise RuntimeError(
                    "anthropic SDK not installed. Run: pip install anthropic"
                )
        return self._client

    def execute(self, mission: Dict, task: Dict) -> Dict:
        """
        Run the agentic loop for this task.
        Returns a result dict with keys: status, summary, artifacts, tokens_used, error.
        """
        agent_id = task.get("agent_id", "agent-0")
        mission_id = mission.get("id") or task.get("mission_id", "unknown")

        system_prompt = _load_system_prompt(agent_id)
        task_prompt = _build_task_prompt(mission, task)

        tool_executor = ToolExecutor(mission_id, sandbox=self._sandbox)
        client = self._get_client()

        messages = [{"role": "user", "content": task_prompt}]
        total_tokens = 0

        logger.info(
            "Starting LLM execution: task=%s agent=%s mission=%s",
            task.get("id"), agent_id, mission_id,
        )

        for iteration in range(_MAX_TOOL_ITERATIONS):
            try:
                response = client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=_TOOLS,
                    messages=messages,
                )
            except Exception as exc:
                logger.error("LLM call failed (iteration %d): %s", iteration, exc)
                return {
                    "status": "failed",
                    "summary": f"LLM call failed: {exc}",
                    "artifacts": [],
                    "tokens_used": total_tokens,
                    "error": str(exc),
                }

            total_tokens += (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)

            # Append assistant response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # ── Terminal: no more tool calls ──────────────────────────────
            if response.stop_reason == "end_turn":
                # Agent finished without calling write_output — still record
                final_text = _extract_text(response.content)
                if tool_executor.output_signal:
                    result = tool_executor.output_signal
                else:
                    result = {
                        "status": "done",
                        "summary": final_text[:2000] if final_text else "Task completed (no structured output).",
                        "implementation_notes": [],
                        "artifacts": [],
                    }
                result["tokens_used"] = total_tokens
                result["iterations"] = iteration + 1
                logger.info("Task complete: %s (tokens=%d)", task.get("id"), total_tokens)
                return result

            # ── Tool use ──────────────────────────────────────────────────
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_result = tool_executor.run(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_result,
                })

                logger.debug("Tool %s → %s chars", block.name, len(tool_result))

                # write_output signals task completion
                if block.name == "write_output" and tool_executor.output_signal:
                    # Append tool results and return
                    messages.append({"role": "user", "content": tool_results})
                    result = {**tool_executor.output_signal, "tokens_used": total_tokens, "iterations": iteration + 1}
                    logger.info(
                        "Task done via write_output: %s status=%s tokens=%d",
                        task.get("id"), result.get("status"), total_tokens,
                    )
                    return result

            messages.append({"role": "user", "content": tool_results})

        # Max iterations reached
        logger.warning("Max iterations (%d) reached for task %s", _MAX_TOOL_ITERATIONS, task.get("id"))
        return {
            "status": "failed",
            "summary": f"Max tool iterations ({_MAX_TOOL_ITERATIONS}) reached without completion.",
            "artifacts": _list_workspace_files(_workspace(mission_id)),
            "tokens_used": total_tokens,
            "iterations": _MAX_TOOL_ITERATIONS,
            "error": "max_iterations_exceeded",
        }


def _extract_text(content) -> str:
    if not content:
        return ""
    parts = []
    for block in content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


# ─── Thread-safe execution manager ───────────────────────────────────────────

class TaskExecutionManager:
    """
    Manages non-blocking task execution.
    TaskRunner calls start_execution() to fire off a thread, then
    calls check_result() on each tick to see if it finished.
    """

    _EXEC_STATUS_KEY = "_exec_status"       # "pending" | "running" | "done" | "failed"
    _EXEC_RESULT_KEY = "_exec_result"       # result dict once done
    _EXEC_STARTED_KEY = "_exec_started_at"  # ISO timestamp

    def __init__(
        self,
        executor: Optional[AgentExecutor] = None,
        sandbox: Optional[SandboxConfig] = None,
    ):
        self._executor = executor or AgentExecutor(sandbox=sandbox)
        self._lock = threading.Lock()

    def is_execution_started(self, task: Dict) -> bool:
        details = task.get("details") or {}
        return details.get(self._EXEC_STATUS_KEY) in {"running", "done", "failed"}

    def execution_status(self, task: Dict) -> Optional[str]:
        details = task.get("details") or {}
        return details.get(self._EXEC_STATUS_KEY)

    def get_result(self, task: Dict) -> Optional[Dict]:
        details = task.get("details") or {}
        return details.get(self._EXEC_RESULT_KEY)

    def start_execution(
        self,
        mission: Dict,
        task: Dict,
        task_repository,
    ) -> None:
        """
        Mark task as executing and start a background thread.
        Non-blocking — returns immediately.
        """
        task_id = task["id"]
        details = dict(task.get("details") or {})
        details[self._EXEC_STATUS_KEY] = "running"
        details[self._EXEC_STARTED_KEY] = datetime.now(timezone.utc).isoformat()
        task_repository.update_task_details(task_id, details)

        thread = threading.Thread(
            target=self._run_in_background,
            args=(mission, task, task_repository),
            daemon=True,
            name=f"exec-{task_id[:8]}",
        )
        thread.start()
        logger.info("Execution thread started for task %s", task_id)

    def _run_in_background(
        self,
        mission: Dict,
        task: Dict,
        task_repository,
    ) -> None:
        task_id = task["id"]
        try:
            result = self._executor.execute(mission, task)
            final_status = "done" if result.get("status") in {"done", None} else "failed"
        except Exception as exc:
            logger.exception("Unhandled error executing task %s: %s", task_id, exc)
            result = {
                "status": "failed",
                "summary": f"Unhandled executor error: {exc}",
                "error": str(exc),
                "tokens_used": 0,
            }
            final_status = "failed"

        # Write result back to DB (thread-safe read-modify-write)
        with self._lock:
            try:
                fresh_task = task_repository.get_task(task_id)
                details = dict((fresh_task or {}).get("details") or {})
            except Exception:
                details = dict(task.get("details") or {})

            details[self._EXEC_STATUS_KEY] = final_status
            details[self._EXEC_RESULT_KEY] = result
            try:
                task_repository.update_task_details(task_id, details)
            except Exception as exc:
                logger.error("Failed to write exec result for task %s: %s", task_id, exc)

        logger.info(
            "Task %s execution finished: status=%s tokens=%s",
            task_id, final_status, result.get("tokens_used", "?"),
        )


# ─── Module-level singleton (lazy, shared across all TaskRunner instances) ────

_default_manager: Optional[TaskExecutionManager] = None
_manager_lock = threading.Lock()


def get_execution_manager() -> TaskExecutionManager:
    global _default_manager
    if _default_manager is None:
        with _manager_lock:
            if _default_manager is None:
                _default_manager = TaskExecutionManager()
    return _default_manager
