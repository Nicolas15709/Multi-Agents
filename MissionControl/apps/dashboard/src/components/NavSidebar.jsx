import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Bot, Target, CircleDot, History, Cpu,
  Settings, Building2, Home, Globe, Star, Zap, Shield, Rocket,
  Brain, Layers, Code2, Terminal, Paintbrush, Search, Activity, Wifi,
  Sparkles, Briefcase, BookOpen, FlaskConical, Microscope,
  Satellite, Landmark, ChevronDown, ChevronRight,
  LayoutTemplate, SlidersHorizontal, LogOut,
} from 'lucide-react'

const ICON_MAP = {
  building: Building2, home: Home, globe: Globe, star: Star,
  zap: Zap, shield: Shield, rocket: Rocket, brain: Brain, bot: Bot,
  layers: Layers, target: Target, code: Code2, terminal: Terminal,
  paint: Paintbrush, search: Search, activity: Activity, wifi: Wifi,
  sparkles: Sparkles, briefcase: Briefcase, book: BookOpen, flask: FlaskConical,
  microscope: Microscope, satellite: Satellite, landmark: Landmark,
}

const AVATAR_ICON_MAP = {
  building: Building2, home: Home, cpu: Cpu, globe: Globe,
  star: Star, zap: Zap, shield: Shield, rocket: Rocket, brain: Brain, bot: Bot,
  layers: Layers, target: Target, code: Code2, terminal: Terminal,
  paint: Paintbrush, search: Search, activity: Activity, wifi: Wifi,
  sparkles: Sparkles, briefcase: Briefcase, book: BookOpen, flask: FlaskConical,
  microscope: Microscope, satellite: Satellite, landmark: Landmark,
}

const AGENT_PALETTE = ['#7c6aef', '#4fc3f7', '#f472b6', '#00ddb5', '#f5a623', '#a78bfa', '#ec4899']

const NAV_SECTIONS = [
  {
    id: 'main',
    label: 'Principal',
    items: [
      { id: 'overview',  label: 'Dashboard',  Icon: LayoutDashboard, badge: null },
      { id: 'missions',  label: 'Misiones',   Icon: Target,           badge: 'activeMission' },
      { id: 'agents',    label: 'Agentes',    Icon: Bot,              badge: 'activeAgents' },
      { id: 'tasks',     label: 'Tareas',     Icon: CircleDot,        badge: 'runningTasks' },
      { id: 'timeline',  label: 'Timeline',   Icon: History,          badge: null },
    ],
  },
  {
    id: 'operations',
    label: 'Operaciones',
    items: [
      { id: 'templates', label: 'Plantillas', Icon: LayoutTemplate,   badge: null },
      { id: 'system',    label: 'Sistema',    Icon: Cpu,              badge: 'systemStatus' },
    ],
  },
  {
    id: 'config',
    label: 'Configuraci\u00f3n',
    items: [
      { id: 'settings',  label: 'Ajustes',    Icon: SlidersHorizontal, badge: null },
    ],
  },
]

function resolveBadge(badgeKey, agents, activeMission) {
  if (!badgeKey) return null
  if (badgeKey === 'activeMission' && activeMission?.status === 'running') return '\u25cf'
  if (badgeKey === 'activeAgents') {
    const count = agents.filter(a => a.state !== 'idle').length
    return count > 0 ? count : null
  }
  return null
}

export function NavSidebar({ officeConfig, agents = [], activeView, onViewChange, onOpenCustomizer, activeMission, collapsed, onLogout }) {
  const [expanded, setExpanded] = useState({ main: true, operations: true, config: true, team: true })
  const { name, icon, color, description } = officeConfig
  const OfficeIcon = ICON_MAP[icon] ?? Building2

  const toggleSection = (id) => setExpanded(v => ({ ...v, [id]: !v[id] }))

  const sidebarClasses = `nav-sidebar${collapsed ? ' nav-sidebar--collapsed' : ''}`

  return (
    <aside className={sidebarClasses} role="navigation" aria-label="Navegaci\u00f3n principal">
      {/* Office Identity Header */}
      <div className="nav-sidebar-header">
        <motion.div
          className="nav-sidebar-identity-icon"
          style={{ background: `${color}18`, border: `1.5px solid ${color}35` }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.97 }}
          onClick={onOpenCustomizer}
        >
          <OfficeIcon size={16} style={{ color }} />
        </motion.div>
        <div className="nav-sidebar-identity-text">
          <div className="nav-sidebar-identity-name">{name}</div>
          <div className="nav-sidebar-identity-desc">{description || 'Virtual Agency'}</div>
        </div>
        <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}`, flexShrink: 0 }} />
      </div>

      {/* Nav */}
      <nav className="nav-sidebar-nav">
        {NAV_SECTIONS.map(section => (
          <div key={section.id} style={{ marginBottom: '8px' }}>
            <SectionHeader
              label={section.label}
              expanded={expanded[section.id]}
              onToggle={() => toggleSection(section.id)}
              collapsed={collapsed}
            />
            <AnimatePresence initial={false}>
              {expanded[section.id] && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.18, ease: 'easeInOut' }}
                  style={{ overflow: 'hidden' }}
                >
                  <div style={{ paddingTop: '2px', display: 'flex', flexDirection: 'column', gap: '1px' }}>
                    {section.items.map(({ id, label, Icon, badge }) => {
                      const badgeValue = resolveBadge(badge, agents, activeMission)
                      return (
                        <NavItem
                          key={id}
                          id={id}
                          label={label}
                          Icon={Icon}
                          active={activeView === id}
                          color={color}
                          badge={badgeValue}
                          collapsed={collapsed}
                          onClick={() => onViewChange(id)}
                        />
                      )
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}

        {/* Team section */}
        <div>
          <SectionHeader
            label="Equipo"
            expanded={expanded.team}
            onToggle={() => toggleSection('team')}
            badge={agents.filter(a => a.state !== 'idle').length || null}
            collapsed={collapsed}
          />
          <AnimatePresence initial={false}>
            {expanded.team && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.18, ease: 'easeInOut' }}
                style={{ overflow: 'hidden' }}
              >
                <div style={{ paddingTop: '2px' }}>
                  {agents.length === 0 ? (
                    <div style={{ fontSize: '11px', color: 'var(--muted)', padding: '8px 10px', fontStyle: 'italic' }}>
                      Sin agentes activos
                    </div>
                  ) : (
                    agents.map((agent, idx) => (
                      <AgentRow
                        key={agent.agent_id}
                        agent={agent}
                        color={AGENT_PALETTE[idx % AGENT_PALETTE.length]}
                        collapsed={collapsed}
                        onClick={() => onViewChange('agents')}
                      />
                    ))
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </nav>

      {/* Footer */}
      <div className="nav-footer">
        <button className="nav-footer-btn" onClick={onOpenCustomizer}>
          <div className="nav-sidebar-identity-icon" style={{ width: '27px', height: '27px', background: `${color}15`, border: `1px solid ${color}25` }}>
            <Settings size={13} style={{ color }} />
          </div>
          <span className="nav-footer-label">Personalizar oficina</span>
        </button>
        {onLogout && (
          <button
            className="nav-footer-btn"
            onClick={onLogout}
            style={{ color: 'var(--muted)' }}
            title="Cerrar sesión"
          >
            <div className="nav-sidebar-identity-icon" style={{ width: '27px', height: '27px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}>
              <LogOut size={13} style={{ color: '#f87171' }} />
            </div>
            <span className="nav-footer-label" style={{ color: '#f87171' }}>Cerrar sesión</span>
          </button>
        )}
      </div>
    </aside>
  )
}

function NavItem({ id, label, Icon, active, color, badge, collapsed, onClick }) {
  const cls = `nav-item${active ? ' nav-item--active' : ''}`
  return (
    <motion.button
      className={cls}
      onClick={onClick}
      style={active ? { borderLeft: `2px solid ${color}`, background: `${color}12` } : { borderLeft: '2px solid transparent' }}
      whileHover={!active ? { background: 'rgba(255,255,255,0.04)' } : undefined}
      whileTap={{ scale: 0.98 }}
      aria-current={active ? 'page' : undefined}
    >
      <Icon size={14} className="nav-item-icon" />
      <span className="nav-item-label">{label}</span>
      {badge != null && (
        <span className="nav-item-badge" style={active ? { background: `${color}35`, color } : undefined}>
          {badge}
        </span>
      )}
      {active && (
        <motion.div
          layoutId="nav-active-dot"
          style={{ width: '4px', height: '4px', borderRadius: '50%', background: color, flexShrink: 0 }}
        />
      )}
    </motion.button>
  )
}

function SectionHeader({ label, expanded, onToggle, badge, collapsed }) {
  return (
    <button className="nav-section-header" onClick={onToggle}>
      <span className="nav-section-label">{label}</span>
      {badge != null && badge > 0 && (
        <span style={{
          fontSize: '9px', fontWeight: 700, padding: '1px 5px', borderRadius: '10px',
          background: 'rgba(0,221,181,0.12)', color: '#00ddb5',
          border: '1px solid rgba(0,221,181,0.18)',
        }}>
          {badge}
        </span>
      )}
      <span style={{ marginLeft: 'auto', color: 'var(--muted)', opacity: 0.5 }}>
        {expanded ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
      </span>
    </button>
  )
}

function AgentRow({ agent, color, collapsed, onClick }) {
  const isActive = agent.state !== 'idle'
  const avatarColor = agent.avatar_color ?? color
  const AvatarIcon = AVATAR_ICON_MAP[agent.avatar_icon] ?? Bot

  return (
    <motion.div
      className="nav-agent-row"
      onClick={onClick}
      whileHover={{ background: 'rgba(255,255,255,0.04)' }}
    >
      <div className="nav-agent-avatar" style={{ background: `${avatarColor}22`, border: `1px solid ${avatarColor}40` }}>
        <AvatarIcon size={11} style={{ color: avatarColor }} />
        <div
          className="nav-agent-status-dot"
          style={{
            background: isActive ? 'var(--accent)' : 'rgba(255,255,255,0.15)',
            boxShadow: isActive ? '0 0 4px var(--accent)' : 'none',
          }}
        />
      </div>
      <div className="nav-agent-info">
        <div className="nav-agent-name">{agent.display_name}</div>
        <div className="nav-agent-state">{agent.state}</div>
      </div>
      {isActive && (
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 1.5, repeat: Infinity }}
          style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--accent)', flexShrink: 0 }}
        />
      )}
    </motion.div>
  )
}
