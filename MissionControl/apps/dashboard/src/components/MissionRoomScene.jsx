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
    director: '/avatars-pixel/supervisor.png',
    finder: '/avatars-pixel/researcher.png',
    'prototype-architect': '/avatars-pixel/designer.png',
    builder: '/avatars-pixel/developer.png',
    improver: '/avatars-pixel/qa.png',
  }
  return map[role] || '/avatars-pixel/supervisor.png'
}

function AgentSprite({ agent, index }) {
  const positions = [
    { top: '16%', left: '12%' },
    { top: '22%', left: '66%' },
    { top: '56%', left: '18%' },
    { top: '48%', left: '70%' },
    { top: '74%', left: '45%' },
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
        <div className="ambient-glow ambient-a" />
        <div className="ambient-glow ambient-b" />

        <div className="iso-platform platform-command">Command</div>
        <div className="iso-platform platform-research">Research</div>
        <div className="iso-platform platform-design">Design</div>
        <div className="iso-platform platform-build">Build</div>
        <div className="iso-platform platform-qa">QA</div>

        <div className="iso-prop prop-command-screen" />
        <div className="iso-prop prop-research-board" />
        <div className="iso-prop prop-design-wall" />
        <div className="iso-prop prop-build-rack" />
        <div className="iso-prop prop-qa-console" />

        <div className="connection connection-a" />
        <div className="connection connection-b" />
        <div className="connection connection-c" />
        <div className="connection connection-d" />

        {agents.map((agent, index) => <AgentSprite key={agent.agent_id} agent={agent} index={index} />)}
      </div>
    </section>
  )
}
