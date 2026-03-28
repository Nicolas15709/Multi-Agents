import fs from 'node:fs';
import path from 'node:path';

function readPrompt(baseDir, promptFile) {
  return fs.readFileSync(path.join(baseDir, '..', promptFile), 'utf8');
}

export async function invokeAgent(agent, payload, options = {}) {
  const { baseDir, contextMessages = [] } = options;
  const prompt = readPrompt(baseDir, agent.promptFile);

  return {
    task_id: payload.task_id,
    agent: agent.id,
    status: 'done',
    prompt_preview: prompt.slice(0, 240),
    received_context_items: contextMessages.length,
    echo: payload,
    note: 'Stub agent invocation. Replace with MCP/OpenClaw session calls.'
  };
}
