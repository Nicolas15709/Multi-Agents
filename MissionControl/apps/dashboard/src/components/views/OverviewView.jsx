import { Suspense, lazy, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Target, Cpu, BarChart3, Clock, Activity, Users, Zap } from 'lucide-react'
import { TaskPanel } from '../TaskPanel'
import { SystemPanel } from '../SystemPanel'
import { MissionInspector } from '../MissionInspector'
import { TimelinePanel } from '../TimelinePanel'
import { ThoughtLogPanel } from '../ThoughtLogPanel'
import { AnimatedNumber } from '../AnimatedNumber'

const PixelOffice = lazy(() =>
  import('../PixelOffice').then(m => ({ default: m.PixelOffice }))
)

// ── Compact inline stat chip ─────────────────────────────────────
function StatChip({ icon: Icon, value, label, color }) {
  return (
    <div style={statChipStyle}>
      <Icon size={11} style={{ color, opacity: 0.85 }} />
      <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-bright)' }}>
        <AnimatedNumber value={typeof value === 'number' ? value : 0} />
      </span>
      <span style={{ fontSize: '10px', color: 'var(--muted)', fontWeight: 500 }}>{label}</span>
    </div>
  )
}

// ── Mission chip (compact) ────────────────────────────────────────
function MissionChip({ activeMission }) {
  const status = activeMission?.status || 'idle'
  const isRunning = status === 'running'
  return (
    <div style={missionChipStyle}>
      <motion.div
        style={{ width: '6px', height: '6px', borderRadius: '50%', background: isRunning ? '#00ddb5' : 'rgba(255,255,255,0.2)', flexShrink: 0 }}
        animate={isRunning ? { opacity: [1, 0.35, 1] } : {}}
        transition={{ duration: 1.4, repeat: Infinity }}
      />
      <span style={{ fontSize: '11px', fontWeight: 600, color: isRunning ? '#00ddb5' : 'var(--muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>
        {activeMission?.title || 'Sin misión activa'}
      </span>
      <span style={{ fontSize: '10px', padding: '1px 6px', borderRadius: '4px', background: isRunning ? 'rgba(0,221,181,0.12)' : 'rgba(255,255,255,0.05)', color: isRunning ? '#00ddb5' : 'var(--muted)', flexShrink: 0 }}>
        {status}
      </span>
    </div>
  )
}

// ── Right panel: mission + intel + tasks + timeline ───────────────
function RightPanel({ activeMission, agents, tasks, stream, progress }) {
  return (
    <div style={rightPanelStyle}>
      {/* Mission compact card */}
      <div style={rightCardStyle}>
        <div className="eyebrow" style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '8px' }}>
          <Target size={10} /> Misión
        </div>
        <div style={{ fontWeight: 700, fontSize: '13px', color: 'var(--text-bright)', lineHeight: 1.3, marginBottom: '4px' }}>
          {activeMission?.title || 'Standby Operacional'}
        </div>
        <p className="muted" style={{ fontSize: '11px', lineHeight: 1.5, margin: 0 }}>
          {activeMission?.goal || 'Esperando instrucciones del sistema.'}
        </p>
        <div style={{ display: 'flex', gap: '5px', marginTop: '8px', flexWrap: 'wrap' }}>
          <span className="state-pill" style={activeMission?.status === 'running' ? {
            background: 'rgba(0,221,181,0.1)', color: '#00ddb5', border: '1px solid rgba(0,221,181,0.15)',
          } : {}}>{activeMission?.status || 'idle'}</span>
          <span className="badge">Mode: {activeMission?.mode || 'Normal'}</span>
        </div>
      </div>

      {/* Strategic Intel */}
      <div style={rightCardStyle}>
        <h2 className="section-title"><Target size={11} /> Strategic Intel</h2>
        <MissionInspector mission={activeMission} tasks={tasks} agents={agents} meta={{}} />
      </div>

      {/* Tasks */}
      <div style={rightCardStyle}>
        <TaskPanel tasks={tasks} />
      </div>

      {/* System */}
      <div style={rightCardStyle}>
        <SystemPanel stream={stream} progress={progress} />
      </div>

      {/* Activity */}
      <div style={{ ...rightCardStyle, flex: 1, minHeight: '120px', overflow: 'hidden' }}>
        <h2 className="section-title"><Activity size={11} /> Actividad</h2>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          <ThoughtLogPanel events={stream.events} />
        </div>
      </div>
    </div>
  )
}

export function OverviewView({ activeMission, agents, tasks, stream, progress, officeConfig }) {
  const stats = useMemo(() => {
    const activeAgents = agents.filter(a => a.state !== 'idle').length
    const completedTasks = tasks.filter(t => t.status === 'done' || t.status === 'completed').length
    return {
      activeAgents,
      completedTasks,
      totalTasks: tasks.length,
      eventCount: stream.events?.length ?? 0,
    }
  }, [agents, tasks, stream.events])

  const isMissionLive = activeMission?.status === 'running'

  return (
    <div style={viewStyle}>
      {/* ── Left: pixel office FULL, no card wrapper ── */}
      <div style={officeWrapStyle}>
        <Suspense fallback={
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div className="muted" style={{ fontSize: '12px' }}>Cargando oficina...</div>
          </div>
        }>
          <PixelOffice agents={agents} officeName={officeConfig?.name ?? ''} />
        </Suspense>

        {/* ── HUD overlay: stats + mission — bottom of office ── */}
        <div style={hudStyle}>
          {/* Left: stats */}
          <div style={hudLeftStyle}>
            <StatChip icon={Users}    value={stats.activeAgents}   label="agentes"  color="#8875ff" />
            <div style={hudDivider} />
            <StatChip icon={BarChart3} value={stats.completedTasks} label="tareas"   color="#00d4a0" />
            <div style={hudDivider} />
            <StatChip icon={Clock}    value={stats.eventCount}      label="eventos"  color="#38bdf8" />
          </div>

          {/* Right: mission status */}
          <MissionChip activeMission={activeMission} />
        </div>

        {/* Office name tag */}
        <div style={officeNameStyle}>
          {isMissionLive && (
            <motion.div
              style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#00ddb5' }}
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.4, repeat: Infinity }}
            />
          )}
          <Cpu size={11} style={{ opacity: 0.5 }} />
          <span>{officeConfig?.name || 'Virtual Agency'}</span>
          <span style={{ opacity: 0.35 }}>·</span>
          <span>{agents.length} agentes</span>
        </div>
      </div>

      {/* ── Right: compact panels ── */}
      <RightPanel
        activeMission={activeMission}
        agents={agents}
        tasks={tasks}
        stream={stream}
        progress={progress}
      />
    </div>
  )
}

// ── Styles ─────────────────────────────────────────────────────────
const viewStyle = {
  flex: 1,
  display: 'flex',
  flexDirection: 'row',
  overflow: 'hidden',
  minHeight: 0,
  gap: 0,
}

const officeWrapStyle = {
  flex: 1,
  minWidth: 0,
  position: 'relative',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
  // No card: no border, no background — just the raw canvas
}

const hudStyle = {
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  padding: '10px 14px 12px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  background: 'linear-gradient(transparent, rgba(5,8,16,0.85) 60%)',
  pointerEvents: 'none',
  zIndex: 10,
  gap: '10px',
}

const hudLeftStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  background: 'rgba(8,11,24,0.7)',
  backdropFilter: 'blur(12px)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: '10px',
  padding: '6px 12px',
  pointerEvents: 'auto',
}

const hudDivider = {
  width: '1px',
  height: '14px',
  background: 'rgba(255,255,255,0.08)',
}

const statChipStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '5px',
}

const missionChipStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '7px',
  background: 'rgba(8,11,24,0.7)',
  backdropFilter: 'blur(12px)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: '10px',
  padding: '6px 12px',
  pointerEvents: 'auto',
  maxWidth: '260px',
}

const officeNameStyle = {
  position: 'absolute',
  top: '12px',
  right: '12px',
  display: 'flex',
  alignItems: 'center',
  gap: '5px',
  fontSize: '11px',
  color: 'rgba(255,255,255,0.45)',
  background: 'rgba(8,11,24,0.55)',
  backdropFilter: 'blur(8px)',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '7px',
  padding: '4px 9px',
  pointerEvents: 'none',
  zIndex: 10,
}

const rightPanelStyle = {
  width: '300px',
  minWidth: '260px',
  maxWidth: '320px',
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  overflowY: 'auto',
  padding: '12px 12px 12px 8px',
  borderLeft: '1px solid rgba(255,255,255,0.05)',
  flexShrink: 0,
}

const rightCardStyle = {
  background: 'rgba(12,17,35,0.6)',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '12px',
  padding: '12px 14px',
  display: 'flex',
  flexDirection: 'column',
  flexShrink: 0,
}
