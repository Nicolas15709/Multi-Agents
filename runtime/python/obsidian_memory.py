"""
Obsidian Memory Bridge for Multi-Agents
Integra automáticamente missions, learnings y decisions en tu bóveda.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from models import Mission, Task, TaskStatus


class ObsidianMemory:
    """Guarda información de misiones en Obsidian."""

    def __init__(self, vault_path: str = None):
        """
        vault_path: ruta a tu bóveda (default: C:\\Users\\Nicolas\\Documents\\Memoria Boveda)
        """
        if vault_path is None:
            vault_path = r"C:\Users\Nicolas\Documents\Memoria Boveda"

        self.vault = Path(vault_path)
        self.missions_dir = self.vault / "missions"
        self.learnings_dir = self.vault / "learnings"
        self.decisions_dir = self.vault / "decisions"
        self.patterns_dir = self.vault / "patterns"

        # Asegurar que existen las carpetas
        self.missions_dir.mkdir(parents=True, exist_ok=True)
        self.learnings_dir.mkdir(parents=True, exist_ok=True)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)

    def save_mission(self, mission: Mission, tasks: List[Task]) -> str:
        """
        Guarda una misión completa con sus tareas y resultados.
        Retorna el path del archivo creado.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{today}-{mission.id}.md"
        filepath = self.missions_dir / filename

        # Agrupar tasks por status
        completed_tasks = [t for t in tasks if t.status == "done"]
        blocked_tasks = [t for t in tasks if t.status in ["blocked", "failed"]]
        pending_tasks = [t for t in tasks if t.status in ["pending", "running"]]

        # Mapeo de agent_id a nombre
        agent_names = {
            "agent-0": "Supervisor",
            "agent-1": "Researcher",
            "agent-2": "Designer",
            "agent-3": "Developer",
            "agent-4": "QA"
        }

        # Agentes únicos que participaron
        agents_used = list(set(t.agent_id for t in tasks))
        agents_str = ", ".join([f"{agent_names.get(aid, aid)}" for aid in agents_used])

        content = f"""# {mission.title}

## 📋 Metadata
- **Fecha:** {today}
- **ID:** {mission.id}
- **Modo:** {mission.mode}
- **Estado:** {mission.status}
- **Prioridad:** {mission.priority}

## 🎯 Objetivo
{mission.goal}

## 👥 Agentes Participantes
{agents_str}

## 📝 Tareas Completadas ({len(completed_tasks)})
"""
        for task in completed_tasks:
            agent_name = agent_names.get(task.agent_id, task.agent_id)
            content += f"- ✅ **{task.title}** ({agent_name})\n"

        if blocked_tasks:
            content += f"\n## ⚠️ Tareas Bloqueadas ({len(blocked_tasks)})\n"
            for task in blocked_tasks:
                agent_name = agent_names.get(task.agent_id, task.agent_id)
                content += f"- ❌ **{task.title}** ({agent_name})\n"

        if pending_tasks:
            content += f"\n## ⏳ Tareas Pendientes ({len(pending_tasks)})\n"
            for task in pending_tasks:
                agent_name = agent_names.get(task.agent_id, task.agent_id)
                content += f"- 🔄 **{task.title}** ({agent_name})\n"

        content += f"""
## 💡 Aprendizajes Clave
_Agrega manualmente después de revisar resultados_

## 🔗 Relacionado
- **Learnings:**
- **Decisiones:**
- **Patterns:**

---
#mision #{mission.mode}
"""

        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def save_learning(self, title: str, insight: str, theme: str = "process",
                     agents: Optional[List[str]] = None, mission_id: Optional[str] = None) -> str:
        """
        Guarda un learning/insight descubierto.
        theme: "technical" | "market" | "process"
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Sanitizar nombre
        safe_title = title.lower().replace(" ", "-")[:50]
        filename = f"{today}-{safe_title}.md"

        theme_map = {
            "technical": "technical",
            "market": "market",
            "process": "process"
        }
        theme_dir = self.learnings_dir / theme_map.get(theme, "process")
        theme_dir.mkdir(parents=True, exist_ok=True)

        filepath = theme_dir / filename

        agent_tags = ""
        if agents:
            agent_tags = " ".join([f"#agente/{agent}" for agent in agents])

        mission_link = f"[[{mission_id}]]" if mission_id else "_none_"

        content = f"""# {title}

## 📋 Metadata
- **Tema:** {theme}
- **Fecha descubierto:** {today}
- **Relevancia:** media
- **Aplicabilidad:** inmediata

## 📝 ¿Qué descubrimos?
{insight}

## 🎯 Por Qué Importa
_Agrega explicación de impacto_

## 💡 Aplicación Práctica
_Agrega pasos de implementación_

## 📚 Fuente
- Misión: {mission_link}
- Agentes: {', '.join(agents) if agents else 'N/A'}

## 🔗 Relacionado
- **Otros learnings:**
- **Decisiones afectadas:**
- **Proyectos relevantes:**

---
#learning #tema/{theme} {agent_tags}
"""

        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def save_decision(self, title: str, decision: str, reasoning: str,
                     impact: str = "proceso") -> str:
        """
        Guarda una decisión importante.
        impact: "proyecto" | "arquitectura" | "proceso"
        """
        today = datetime.now().strftime("%Y-%m-%d")

        safe_title = title.lower().replace(" ", "-")[:50]
        filename = f"{today}-{safe_title}.md"
        filepath = self.decisions_dir / filename

        content = f"""# Decisión: {title}

## 📋 Metadata
- **Fecha:** {today}
- **Impacto:** {impact}

## ❓ La Pregunta
_Agrega la pregunta o dilema original_

## ✅ Decisión Tomada
{decision}

## 🤔 Razonamiento
{reasoning}

## 📊 Contexto
_Agrega contexto y constraints_

## 🔄 Trade-offs
_Agrega qué ganamos y qué perdimos_

## 🔗 Relacionado
- **Misiones afectadas:**
- **Learnings que influyeron:**
- **Patterns relacionados:**

---
#decision #impacto/{impact}
"""

        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def get_agent_context(self, agent_name: str = None) -> str:
        """
        Retorna contexto relevante para un agente (learnings + decisiones recientes).
        Útil para inyectar en prompts de agentes.
        """
        context = []

        # Leer últimos learnings
        learnings = list(self.learnings_dir.rglob("*.md"))
        learnings.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for learning in learnings[:3]:  # Últimos 3
            content = learning.read_text(encoding="utf-8")
            context.append(f"## Learning: {learning.name}\n{content[:200]}...")

        # Leer últimas decisiones
        decisions = list(self.decisions_dir.glob("*.md"))
        decisions.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for decision in decisions[:2]:  # Últimas 2
            content = decision.read_text(encoding="utf-8")
            context.append(f"## Decision: {decision.name}\n{content[:200]}...")

        return "\n---\n".join(context)


# Hook para usar en main.py
def hook_mission_completed(mission: Mission, tasks: List[Task], obsidian: ObsidianMemory = None):
    """
    Llamar después de que una misión se complete.
    Ejemplo en main.py:
        hook_mission_completed(mission, tasks)
    """
    if obsidian is None:
        obsidian = ObsidianMemory()

    filepath = obsidian.save_mission(mission, tasks)
    print(f"✅ Misión guardada en Obsidian: {filepath}")
