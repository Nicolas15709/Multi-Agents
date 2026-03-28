export const mockSnapshot = {
  activeMission: {
    id: 'mission-bootstrap',
    title: 'Bootstrap Mission Control',
    goal: 'Initialize runtime, dashboard and mission pipeline',
    mode: 'software_build',
    priority: 'high',
    status: 'running'
  },
  agents: [
    {
      agent_id: 'agent-0',
      display_name: 'Supervisor',
      role: 'director',
      state: 'planning',
      personality: 'Analytical, direct, focused on deliverables and priority management.'
    },
    {
      agent_id: 'agent-1',
      display_name: 'Researcher',
      role: 'finder',
      state: 'researching',
      personality: 'Curious, factual, meticulous with sources and context.'
    },
    {
      agent_id: 'agent-2',
      display_name: 'Designer',
      role: 'prototype-architect',
      state: 'designing',
      personality: 'Visually sharp, structured, practical about UX and references.'
    },
    {
      agent_id: 'agent-3',
      display_name: 'Developer',
      role: 'builder',
      state: 'building',
      personality: 'Productive, pragmatic, implementation-focused and detail-oriented.'
    },
    {
      agent_id: 'agent-4',
      display_name: 'QA',
      role: 'improver',
      state: 'reviewing',
      personality: 'Critical, supportive, perfectionist and reliability-focused.'
    }
  ],
  stream: {
    events: [
      { id: 1, summary: 'Supervisor inició la planificación de la misión.' },
      { id: 2, summary: 'Researcher recopiló contexto técnico y comercial.' },
      { id: 3, summary: 'Designer está definiendo la estructura visual del dashboard.' }
    ],
    notifications: [
      { id: 1, summary: 'Misión bootstrap creada.' }
    ]
  }
}
