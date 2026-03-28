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

const SCENE_SPRITES = [
  {
    key: 'carpet-main',
    className: 'scene-sprite carpet-main',
    src: '/extracted-assets/scene/floorCarpet_W.png',
    alt: 'Central carpet',
  },
  {
    key: 'carpet-side',
    className: 'scene-sprite carpet-side',
    src: '/extracted-assets/scene/floorCarpet_E.png',
    alt: 'Side carpet',
  },
  {
    key: 'table',
    className: 'scene-sprite table-main',
    src: '/extracted-assets/scene/longTableDecoratedChairsBooks_W.png',
    alt: 'Operations table',
  },
  {
    key: 'shelf-left',
    className: 'scene-sprite shelf-left',
    src: '/extracted-assets/scene/bookcaseWideBooksDesk_W.png',
    alt: 'Research shelf',
  },
  {
    key: 'shelf-right',
    className: 'scene-sprite shelf-right',
    src: '/extracted-assets/scene/bookcaseWideBooksDesk_E.png',
    alt: 'Build shelf',
  },
  {
    key: 'chair-left',
    className: 'scene-sprite chair-left',
    src: '/extracted-assets/scene/libraryChair_W.png',
    alt: 'Left chair',
  },
  {
    key: 'chair-right',
    className: 'scene-sprite chair-right',
    src: '/extracted-assets/scene/libraryChair_E.png',
    alt: 'Right chair',
  },
]

function AgentSprite({ agent, index }) {
  const positions = [
    { top: '18%', left: '13%' },
    { top: '24%', right: '14%' },
    { top: '54%', left: '18%' },
    { top: '54%', right: '16%' },
    { bottom: '14%', left: '43%' },
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
          <p className="muted room-copy">Una oficina isométrica real: piso, paredes, muebles, estaciones activas y un poco de vida.</p>
        </div>
        <div className="meta-chip">Live scene</div>
      </div>

      <div className="iso-room office-room">
        <div className="room-atmosphere room-atmosphere-a" />
        <div className="room-atmosphere room-atmosphere-b" />
        <div className="ceiling-light light-left" />
        <div className="ceiling-light light-right" />

        <div className="room-shell">
          <div className="room-wall wall-back">
            <div className="window-band">
              <div className="window-panel" />
              <div className="window-panel" />
              <div className="window-panel" />
            </div>
            <div className="wall-hud mission-hud">
              <span className="hud-label">Mission throughput</span>
              <div className="hud-bars">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
          <div className="room-wall wall-side">
            <div className="wall-hud diagnostics-hud">
              <span className="hud-label">Diagnostics</span>
              <div className="hud-grid">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>
            <div className="server-rack">
              <span />
              <span />
              <span />
            </div>
          </div>

          <div className="room-floor" />
          <div className="floor-shine" />
          <div className="data-lane data-lane-a" />
          <div className="data-lane data-lane-b" />
        </div>

        {SCENE_SPRITES.map((sprite) => (
          <img key={sprite.key} className={sprite.className} src={sprite.src} alt={sprite.alt} />
        ))}

        <div className="planter planter-left"><span /></div>
        <div className="planter planter-right"><span /></div>
        <div className="console-pod pod-left">
          <div className="pod-screen" />
          <div className="pod-glow" />
        </div>
        <div className="console-pod pod-right">
          <div className="pod-screen" />
          <div className="pod-glow" />
        </div>
        <div className="holo-dais">
          <div className="holo-core" />
          <div className="holo-ring holo-ring-a" />
          <div className="holo-ring holo-ring-b" />
        </div>

        <div className="connection connection-a" />
        <div className="connection connection-b" />
        <div className="connection connection-c" />
        <div className="connection connection-d" />

        {agents.map((agent, index) => <AgentSprite key={agent.agent_id} agent={agent} index={index} />)}
      </div>
    </section>
  )
}
