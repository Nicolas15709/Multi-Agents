import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Target, Plus, ChevronRight, CheckCircle2, AlertCircle,
  Clock, Rocket, Search, Play, Pause, RotateCcw, X,
  BookOpen, Code2, Shield, BarChart3, Cpu,
} from 'lucide-react'
import { MissionHirePanel } from '../MissionHirePanel'
import { MissionLauncher } from '../MissionLauncher'
import { ProblemIntakePanel } from '../ProblemIntakePanel'
import { pauseMission, resumeMission } from '../../runtimeApi'

const STATUS_CONFIG = {
  running:   { label: 'Activa', color: '#00d4a0', bg: 'rgba(0,212,160,0.1)', border: 'rgba(0,212,160,0.2)', Icon: Play },
  idle:      { label: 'En espera', color: '#8875ff', bg: 'rgba(136,117,255,0.1)', border: 'rgba(136,117,255,0.2)', Icon: Clock },
  completed: { label: 'Completada', color: '#38bdf8', bg: 'rgba(56,189,248,0.1)', border: 'rgba(56,189,248,0.2)', Icon: CheckCircle2 },
  failed:    { label: 'Fallida', color: '#ff4d6d', bg: 'rgba(255,77,109,0.1)', border: 'rgba(255,77,109,0.2)', Icon: AlertCircle },
  paused:    { label: 'Pausada', color: '#ffa940', bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.2)', Icon: Pause },
}

const MODE_ICONS = {
  general_operating_request: Cpu,
  software_build: Code2,
  prototype_to_build: Rocket,
  landing_launch: Rocket,
  feature_extension: Code2,
  bugfix_debug: AlertCircle,
  documentation_pack: BookOpen,
  security_review: Shield,
  qa_hardening: Shield,
  research_only: Search,
  marketing_campaign: BarChart3,
  business_audit_proposal: BarChart3,
  maintenance_cycle: RotateCcw,
}

const TABS = [
  { id: 'all', label: 'Todas' },
  { id: 'running', label: 'Activas' },
  { id: 'completed', label: 'Completadas' },
  { id: 'failed', label: 'Fallidas' },
]

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.idle
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '10px',
      fontWeight: 600,
      padding: '2px 7px',
      borderRadius: '20px',
      background: cfg.bg,
      color: cfg.color,
      border: `1px solid ${cfg.border}`,
    }}>
      <cfg.Icon size={9} />
      {cfg.label}
    </span>
  )
}

function MissionRow({ mission, active, onClick }) {
  const ModeIcon = MODE_ICONS[mission.mode] ?? Target
  return (
    <motion.div
      onClick={onClick}
      whileHover={{ background: 'rgba(255,255,255,0.04)' }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 16px',
        cursor: 'pointer',
        borderRadius: '8px',
        background: active ? 'rgba(136,117,255,0.08)' : 'transparent',
        borderLeft: active ? '2px solid #8875ff' : '2px solid transparent',
        transition: 'all 0.12s',
      }}
    >
      <div style={{
        width: '32px',
        height: '32px',
        borderRadius: '8px',
        flexShrink: 0,
        background: 'rgba(136,117,255,0.1)',
        border: '1px solid rgba(136,117,255,0.2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <ModeIcon size={14} style={{ color: '#8875ff' }} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
          <span style={{
            fontSize: '13px',
            fontWeight: 600,
            color: 'var(--text-bright)',
            overflow: 'hidden',
            whiteSpace: 'nowrap',
            textOverflow: 'ellipsis',
          }}>
            {mission.title}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <StatusBadge status={mission.status} />
          {mission.mode && (
            <span style={{
              fontSize: '10px',
              color: 'var(--muted)',
              background: 'rgba(255,255,255,0.05)',
              padding: '1px 6px',
              borderRadius: '4px',
            }}>
              {mission.mode.replace(/_/g, ' ')}
            </span>
          )}
        </div>
      </div>

      {mission.goal && (
        <div style={{
          maxWidth: '200px',
          fontSize: '11px',
          color: 'var(--muted)',
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          textOverflow: 'ellipsis',
          flexShrink: 0,
        }}>
          {mission.goal}
        </div>
      )}

      <ChevronRight size={14} style={{ color: 'var(--muted)', flexShrink: 0 }} />
    </motion.div>
  )
}

function MissionDetail({ mission, missionSummary, tasks, hireRequests, actionApprovals, sharedMemory, agentMessages, onClose, onMissionPatch }) {
  const missionTasks = tasks.filter(task => task.mission_id === mission.id || !task.mission_id)
  const missionApprovals = actionApprovals.filter(item => item.mission_id === mission.id)
  const missionMemory = sharedMemory.filter(item => item.mission_id === mission.id)
  const missionMessages = agentMessages.filter(item => item.mission_id === mission.id)
  const ModeIcon = MODE_ICONS[mission.mode] ?? Target
  const [isTogglingMission, setIsTogglingMission] = useState(false)
  const [missionFeedback, setMissionFeedback] = useState(null)
  const plan = missionSummary?.plan || null

  async function handleMissionToggle(action) {
    try {
      setIsTogglingMission(true)
      setMissionFeedback(null)
      const result = action === 'pause'
        ? await pauseMission(mission.id, { actor: 'dashboard' })
        : await resumeMission(mission.id, { actor: 'dashboard' })
      onMissionPatch?.(mission.id, {
        status: result.status,
        mission_control: result.mission_control,
      })
      setMissionFeedback(action === 'pause' ? 'Mision pausada.' : 'Mision reanudada.')
    } catch (error) {
      setMissionFeedback(error instanceof Error ? error.message : 'No se pudo cambiar el estado de la mision.')
    } finally {
      setIsTogglingMission(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.2 }}
      style={{
        width: '360px',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        borderLeft: '1px solid rgba(255,255,255,0.06)',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '9px',
          flexShrink: 0,
          background: 'rgba(136,117,255,0.1)',
          border: '1px solid rgba(136,117,255,0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <ModeIcon size={16} style={{ color: '#8875ff' }} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-bright)', lineHeight: 1.3 }}>
            {mission.title}
          </div>
          <div style={{ marginTop: '5px' }}>
            <StatusBadge status={mission.status} />
          </div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: '2px' }}>
          <X size={14} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {mission.goal && (
          <div>
            <div style={sectionLabel}>Objetivo</div>
            <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.6, margin: 0 }}>{mission.goal}</p>
          </div>
        )}

        <div>
          <div style={sectionLabel}>Detalles</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {mission.mode && <DetailRow label="Modo" value={mission.mode.replace(/_/g, ' ')} />}
            {mission.priority && <DetailRow label="Prioridad" value={mission.priority} />}
            {mission.created_at && <DetailRow label="Creada" value={new Date(mission.created_at).toLocaleDateString('es')} />}
            {mission.mission_control?.status && <DetailRow label="Autonomia" value={mission.mission_control.status} />}
            {plan?.workflow_version && <DetailRow label="Planner" value={plan.workflow_version} />}
          </div>
        </div>

        {plan && (
          <div>
            <div style={sectionLabel}>Plan Abierto</div>
            <div style={{ display: 'grid', gap: '8px' }}>
              {Array.isArray(plan.domains) && plan.domains.length > 0 && (
                <TokenGroup label="Dominios" values={plan.domains} />
              )}
              {Array.isArray(plan.workstreams) && plan.workstreams.length > 0 && (
                <TokenGroup label="Workstreams" values={plan.workstreams} />
              )}
              {Array.isArray(plan.required_capabilities) && plan.required_capabilities.length > 0 && (
                <TokenGroup label="Capacidades" values={plan.required_capabilities.slice(0, 8)} />
              )}
              {Array.isArray(plan.tool_primitives) && plan.tool_primitives.length > 0 && (
                <TokenGroup label="Tools" values={plan.tool_primitives.slice(0, 8)} />
              )}
              {Array.isArray(plan.risk_flags) && plan.risk_flags.length > 0 && (
                <TokenGroup label="Riesgos" values={plan.risk_flags} tone="danger" />
              )}
              <DetailRow label="Riesgo" value={plan.risk_level || 'low'} />
              <DetailRow label="Approval gate" value={plan.requires_human_approval ? 'required' : 'not required'} />
            </div>
          </div>
        )}

        {mission.mission_control && (
          <div>
            <div style={sectionLabel}>Budget Autonomo</div>
            <div style={{ display: 'grid', gap: '10px' }}>
              <BudgetMeter label="Pasos" used={mission.mission_control.autonomous_steps_used} max={mission.mission_control.max_autonomous_steps} />
              <BudgetMeter label="Tokens estimados" used={mission.mission_control.estimated_tokens_used} max={mission.mission_control.max_estimated_tokens} />
              <BudgetMeter label="Ticks runtime" used={mission.mission_control.runtime_ticks_used} max={mission.mission_control.max_runtime_ticks} />
              <BudgetMeter label="Hires dinamicos" used={mission.mission_control.dynamic_hires_used} max={mission.mission_control.max_dynamic_hires} />
              {mission.mission_control.action_budgets && Object.keys(mission.mission_control.action_budgets).length > 0 && (
                <TokenGroup label="Action budgets" values={Object.entries(mission.mission_control.action_budgets).map(([key, value]) => `${key}:${value}`)} />
              )}
            </div>
          </div>
        )}

        {(missionApprovals.length > 0 || missionMemory.length > 0 || missionMessages.length > 0) && (
          <div>
            <div style={sectionLabel}>Coordinacion</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <DetailRow label="Approvals" value={String(missionApprovals.length)} />
              <DetailRow label="Shared memory" value={String(missionMemory.length)} />
              <DetailRow label="Agent messages" value={String(missionMessages.length)} />
            </div>
          </div>
        )}

        <div>
          <div style={sectionLabel}>Control</div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => handleMissionToggle('pause')} disabled={isTogglingMission || mission.status === 'completed'} style={secondaryBtn}>
              <Pause size={12} />
              Pausar
            </button>
            <button type="button" onClick={() => handleMissionToggle('resume')} disabled={isTogglingMission || mission.status === 'completed'} style={secondaryBtn}>
              <Play size={12} />
              Reanudar
            </button>
          </div>
          {missionFeedback && (
            <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--muted)' }}>
              {missionFeedback}
            </div>
          )}
        </div>

        {missionTasks.length > 0 && (
          <div>
            <div style={sectionLabel}>Tareas ({missionTasks.length})</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {missionTasks.slice(0, 8).map(task => (
                <div key={task.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)' }}>
                  <TaskStatusDot status={task.status} />
                  <span style={{ fontSize: '11px', color: 'var(--text)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                    {task.title}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <MissionHirePanel mission={mission} hireRequests={hireRequests} />
      </div>
    </motion.div>
  )
}

function TaskStatusDot({ status }) {
  const color = status === 'done' || status === 'completed'
    ? '#00d4a0'
    : status === 'running' || status === 'in_progress'
      ? '#8875ff'
      : status === 'blocked' || status === 'failed'
        ? '#ff4d6d'
        : 'rgba(255,255,255,0.2)'
  return <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: color, flexShrink: 0 }} />
}

function DetailRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
      <span style={{ color: 'var(--muted)' }}>{label}</span>
      <span style={{ color: 'var(--text)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

function TokenGroup({ label, values, tone = 'default' }) {
  const tokenStyle = tone === 'danger'
    ? { background: 'rgba(255,77,109,0.08)', border: '1px solid rgba(255,77,109,0.2)', color: '#ff9a9a' }
    : { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--text)' }
  return (
    <div style={{ display: 'grid', gap: '6px' }}>
      <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{label}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {values.map(value => (
          <span
            key={`${label}-${value}`}
            style={{
              fontSize: '10px',
              padding: '3px 7px',
              borderRadius: '999px',
              ...tokenStyle,
            }}
          >
            {String(value).replace(/_/g, ' ')}
          </span>
        ))}
      </div>
    </div>
  )
}

function BudgetMeter({ label, used = 0, max = 0 }) {
  const safeUsed = Number(used) || 0
  const safeMax = Number(max) || 0
  const percent = safeMax > 0 ? Math.min(100, Math.round((safeUsed / safeMax) * 100)) : 0
  const isHigh = percent >= 85
  return (
    <div style={{ display: 'grid', gap: '5px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
        <span style={{ color: 'var(--muted)' }}>{label}</span>
        <span style={{ color: isHigh ? '#ff9a9a' : 'var(--text)' }}>{safeUsed} / {safeMax || 'inf'}</span>
      </div>
      <div style={{ height: '6px', borderRadius: '999px', background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        <div
          style={{
            width: `${percent}%`,
            height: '100%',
            background: isHigh ? 'linear-gradient(90deg, #ff7b7b, #ff4d6d)' : 'linear-gradient(90deg, #38bdf8, #00d4a0)',
          }}
        />
      </div>
    </div>
  )
}

const sectionLabel = {
  fontSize: '10px',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: 'var(--muted)',
  marginBottom: '8px',
}

function EmptyMissions() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: '12px', padding: '60px 0' }}>
      <div style={{ width: '56px', height: '56px', borderRadius: '14px', background: 'rgba(136,117,255,0.08)', border: '1px solid rgba(136,117,255,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Target size={24} style={{ color: '#8875ff', opacity: 0.6 }} />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '4px' }}>Sin misiones aun</div>
        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>Lanza tu primera mision para empezar.</div>
      </div>
    </div>
  )
}

export function MissionsView({ activeMission, missions = [], missionSummaries = {}, agents, tasks, intakeRequests = [], hireRequests = [], sharedMemory = [], agentMessages = [], actionApprovals = [] }) {
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const [showLauncher, setShowLauncher] = useState(false)
  const [missionPatches, setMissionPatches] = useState({})

  const allMissions = useMemo(() => {
    if (missions.length > 0) {
      return missions.map(mission => ({ ...mission, ...(missionPatches[mission.id] || {}) }))
    }
    if (activeMission) {
      return [{ ...activeMission, ...(missionPatches[activeMission.id] || {}) }]
    }
    return []
  }, [missions, activeMission, missionPatches])

  function patchMission(missionId, patch) {
    setMissionPatches(current => ({
      ...current,
      [missionId]: { ...(current[missionId] || {}), ...patch },
    }))
    setSelected(current => (current?.id === missionId ? { ...current, ...patch } : current))
  }

  const filtered = useMemo(() => {
    return allMissions.filter(mission => {
      if (tab !== 'all' && mission.status !== tab) return false
      if (search && !mission.title?.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [allMissions, tab, search])

  const tabCounts = useMemo(() => ({
    all: allMissions.length,
    running: allMissions.filter(mission => mission.status === 'running').length,
    completed: allMissions.filter(mission => mission.status === 'completed').length,
    failed: allMissions.filter(mission => mission.status === 'failed').length,
  }), [allMissions])

  return (
    <div className="view-shell">
      <div className="view-header">
        <div>
          <h1 className="view-title">Misiones</h1>
          <p className="view-subtitle">Gestiona misiones y recibe problemas nuevos desde dashboard, movil u OpenClaw.</p>
        </div>
        <button onClick={() => setShowLauncher(value => !value)} style={primaryBtn}>
          <Plus size={14} />
          Entrada rapida
        </button>
      </div>

      <AnimatePresence>
        {showLauncher && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden', marginBottom: '8px' }}
          >
            <div style={{ padding: '16px', background: 'rgba(136,117,255,0.05)', border: '1px solid rgba(136,117,255,0.12)', borderRadius: '10px', position: 'relative' }}>
              <button onClick={() => setShowLauncher(false)} style={{ position: 'absolute', top: '12px', right: '12px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)' }}>
                <X size={14} />
              </button>
              <div className="mission-action-grid">
                <MissionLauncher />
                <ProblemIntakePanel requests={intakeRequests} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div style={filterBar}>
        <div style={{ display: 'flex', gap: '2px', background: 'rgba(255,255,255,0.04)', padding: '3px', borderRadius: '8px' }}>
          {TABS.map(item => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              style={{
                ...tabBtn,
                background: tab === item.id ? 'rgba(136,117,255,0.2)' : 'transparent',
                color: tab === item.id ? '#a899ff' : 'var(--muted)',
              }}
            >
              {item.label}
              {tabCounts[item.id] > 0 && (
                <span style={{ ...countBadge, background: tab === item.id ? 'rgba(136,117,255,0.3)' : 'rgba(255,255,255,0.08)' }}>
                  {tabCounts[item.id]}
                </span>
              )}
            </button>
          ))}
        </div>

        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <Search size={12} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
          <input
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Buscar misiones..."
            style={searchInput}
          />
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ flex: 1, overflowY: 'auto', background: 'rgba(255,255,255,0.02)' }}>
          {filtered.length === 0 ? (
            <EmptyMissions />
          ) : (
            <div style={{ padding: '8px' }}>
              {filtered.map(mission => (
                <MissionRow
                  key={mission.id}
                  mission={mission}
                  active={selected?.id === mission.id}
                  onClick={() => setSelected(selected?.id === mission.id ? null : mission)}
                />
              ))}
            </div>
          )}
        </div>

        <AnimatePresence>
          {selected && (
            <MissionDetail
              mission={selected}
              missionSummary={missionSummaries[selected.id]}
              tasks={tasks}
              hireRequests={hireRequests}
              actionApprovals={actionApprovals}
              sharedMemory={sharedMemory}
              agentMessages={agentMessages}
              onClose={() => setSelected(null)}
              onMissionPatch={patchMission}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

const primaryBtn = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  padding: '7px 14px',
  borderRadius: '8px',
  fontSize: '13px',
  fontWeight: 600,
  background: 'rgba(136,117,255,0.2)',
  color: '#a899ff',
  border: '1px solid rgba(136,117,255,0.3)',
  cursor: 'pointer',
  fontFamily: 'Inter, system-ui, sans-serif',
  flexShrink: 0,
}

const secondaryBtn = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  padding: '7px 10px',
  borderRadius: '8px',
  fontSize: '11px',
  fontWeight: 600,
  background: 'rgba(255,255,255,0.05)',
  color: 'var(--text)',
  border: '1px solid rgba(255,255,255,0.08)',
  cursor: 'pointer',
  fontFamily: 'Inter, system-ui, sans-serif',
}

const filterBar = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  flexWrap: 'wrap',
}

const tabBtn = {
  padding: '4px 10px',
  borderRadius: '5px',
  border: 'none',
  cursor: 'pointer',
  fontSize: '12px',
  fontWeight: 500,
  display: 'flex',
  alignItems: 'center',
  gap: '5px',
  fontFamily: 'Inter, system-ui, sans-serif',
  transition: 'all 0.12s',
}

const countBadge = {
  fontSize: '10px',
  fontWeight: 700,
  padding: '0 5px',
  borderRadius: '8px',
  minWidth: '16px',
  textAlign: 'center',
}

const searchInput = {
  paddingLeft: '28px',
  paddingRight: '10px',
  paddingTop: '6px',
  paddingBottom: '6px',
  background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '7px',
  color: 'var(--text)',
  fontSize: '12px',
  fontFamily: 'Inter, system-ui, sans-serif',
  outline: 'none',
  width: '180px',
}
