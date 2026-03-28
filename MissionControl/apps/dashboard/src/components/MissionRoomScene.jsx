function stationLabel(role) {
  const map = {
    director: 'Command Table',
    finder: 'Research Desk',
    'prototype-architect': 'Design Bay',
    builder: 'Build Terminal',
    improver: 'QA Lab',
  }
  return map[role] || 'Ops Station'
}

function activityLabel(agent) {
  const map = {
    planning: 'planning mission',
    researching: 'researching context',
    designing: 'designing flow',
    building: 'building runtime',
    reviewing: 'reviewing output',
    blocked: 'blocked',
    idle: 'standby',
  }
  return map[agent.state] || agent.state
}

function avatarAsset(role) {
  const map = {
    director: '/avatars/supervisor.svg',
    finder: '/avatars/researcher.svg',
    'prototype-architect': '/avatars/designer.svg',
    builder: '/avatars/developer.svg',
    improver: '/avatars/qa.svg',
  }
  return map[role] || '/avatars/supervisor.svg'
}

function AgentSprite({ agent, index }) {
  const positions = [
    { top: '14%', left: '10%' },
    { top: '26%', left: '60%' },
    { top: '58%', left: '18%' },
    { top: '50%', left: '66%' },
    { top: '72%', left: '44%' },
  ]

  return (
    <div className={`agent-sprite state-${agent.state}`} style={positions[index % positions.length]}>
      <div className="agent-tag">
        <strong>{agent.display_name}</strong>
        <span>{activityLabel(agent)}</span>
      </div>
      <div className="agent-avatar portrait-avatar">
        <img src={avatarAsset(agent.role)} alt={agent.display_name} className="agent-portrait" />
      </div>
      <div className="activity-ring" />
      <div className="station-marker">{stationLabel(agent.role)}</div>
    </div>
  )
}

export function MissionRoomScene({ agents = [] }) {
  return (
    <section className="panel iso-room-panel">
      <div className="room-header">
        <div>
          <h2 className="section-title">Mission room</h2>
          <p className="muted room-copy">Escena operativa con agentes visibles, estaciones y actividad en curso.</p>
        </div>
        <div className="meta-chip">Live scene</div>
      </div>

      <div className="iso-room">
        <div className="iso-grid" />
        <div className="iso-platform platform-command">Command</div>
        <div className="iso-platform platform-research">Research</div>
        <div className="iso-platform platform-design">Design</div>
        <div className="iso-platform platform-build">Build</div>
        <div className="iso-platform platform-qa">QA</div>

        <div className="connection connection-a" />
        <div className="connection connection-b" />
        <div className="connection connection-c" />
        <div className="connection connection-d" />

        {agents.map((agent, index) => <AgentSprite key={agent.agent_id} agent={agent} index={index} />)}
      </div>
    </section>
  )
}
