import { Zap, Wifi, WifiOff, PanelLeftClose, PanelLeft } from 'lucide-react'

const VIEW_LABELS = {
  overview: 'Dashboard',
  missions: 'Misiones',
  agents: 'Agentes',
  tasks: 'Tareas',
  timeline: 'Timeline',
  templates: 'Plantillas',
  system: 'Sistema',
  settings: 'Configuraci\u00f3n',
}

export function TopBar({ view, status, connection, sidebarCollapsed, onToggleSidebar, officeConfig, meta }) {
  const isLive = status.source === 'runtime'
  const isConnected = connection.state === 'connected'

  return (
    <div className="topbar">
      <div className="topbar-left">
        <button
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label={sidebarCollapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
        >
          {sidebarCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
        <span style={{ fontSize: '12px', color: 'var(--muted)' }}>{officeConfig?.name ?? 'Virtual Agency'}</span>
        <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.15)' }}>/</span>
        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-bright)' }}>
          {VIEW_LABELS[view] ?? 'Dashboard'}
        </span>
      </div>

      {view === 'overview' && meta && (
        <div className="topbar-center">
          <div className="topbar-kpi">
            <span className="topbar-kpi-value">{meta.agentCount ?? 0}</span> agentes
          </div>
          <div className="topbar-kpi-divider" />
          <div className="topbar-kpi">
            <span className="topbar-kpi-value">{meta.taskCount ?? 0}</span> tareas
          </div>
          <div className="topbar-kpi-divider" />
          <div className="topbar-kpi">
            <span className="topbar-kpi-value">{meta.missionCount ?? 0}</span> misiones
          </div>
        </div>
      )}

      <div className="topbar-right">
        <div className={`live-pill ${isLive ? 'is-live' : 'is-fallback'}`}>
          <Zap size={10} fill="currentColor" />
          {isLive ? 'Live Runtime' : 'Mock Mode'}
        </div>
        <div className="badge" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          {isConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
          {connection.state}
        </div>
      </div>
    </div>
  )
}
