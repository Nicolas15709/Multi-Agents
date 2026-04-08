export function createInitialPlan(goal) {
  return {
    task_id: `task-${Date.now()}`,
    from: 'user',
    to: 'agent-0',
    goal,
    context: {
      project: 'Virtual Agency',
      constraints: [
        'ARM VPS friendly',
        '128k context safety',
        'persistent state required'
      ],
      artifacts: [],
      dependencies: []
    },
    deliverable: {
      format: 'json',
      acceptance_criteria: [
        'clear plan',
        'research summary if needed',
        'prototype/design specification when relevant',
        'implementation artifact',
        'QA result'
      ]
    },
    priority: 'high'
  };
}

export function nextAgentFromWorkflow(currentAgentId, workflow = []) {
  const index = workflow.indexOf(currentAgentId);
  if (index === -1 || index === workflow.length - 1) return null;
  return workflow[index + 1];
}

