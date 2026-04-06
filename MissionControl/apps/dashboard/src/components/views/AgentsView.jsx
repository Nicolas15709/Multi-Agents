import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bot, Activity, Search, GitBranch, List, X, Brain, Code2, Shield, Microscope,
  Paintbrush, Plus, Check, Building2, Home, Cpu, Globe, Star, Zap, Rocket,
  Layers, Target, Terminal, Wifi, Coffee, Music, Camera, Smile, Heart, Flame,
  TreePine, Mountain, Sun, Moon, Cloud, Sparkles, Crown, Swords, Briefcase,
  BookOpen, FlaskConical, Satellite, Landmark, Palette,
} from 'lucide-react'
import { AGENT_AVATAR_COLORS, DEFAULT_AGENT_ICON, PIXEL_AVATAR_PRESETS } from '../agentProfiles'

const AGENT_PALETTE = ['#8875ff', '#38bdf8', '#f472b6', '#00d4a0', '#ffa940', '#8b5cf6', '#ec4899']

const ROLE_ICONS = {
  supervisor: Brain, researcher: Microscope, developer: Code2,
  designer: Paintbrush, qa: Shield, default: Bot,
}

const AVATAR_ICONS = {
  building: Building2, home: Home, cpu: Cpu, globe: Globe,
  star: Star, zap: Zap, rocket: Rocket, brain: Brain,
  bot: Bot, layers: Layers, target: Target, code: Code2,
  terminal: Terminal, paint: Paintbrush, search: Search,
  activity: Activity, wifi: Wifi, coffee: Coffee, music: Music,
  camera: Camera, smile: Smile, heart: Heart, flame: Flame,
  tree: TreePine, mountain: Mountain, sun: Sun, moon: Moon,
  cloud: Cloud, sparkles: Sparkles, crown: Crown, swords: Swords,
  briefcase: Briefcase, book: BookOpen, flask: FlaskConical,
  microscope: Microscope, satellite: Satellite, landmark: Landmark,
}

const AVATAR_CHOICES = Object.keys(AVATAR_ICONS)

const STATUS_CONFIG = {
  running: { color: '#00d4a0', label: 'Activo', pulse: true },
  active: { color: '#00d4a0', label: 'Activo', pulse: true },
  working: { color: '#00d4a0', label: 'Trabajando', pulse: true },
  idle: { color: 'rgba(255,255,255,0.25)', label: 'Idle', pulse: false },
  blocked: { color: '#ff4d6d', label: 'Bloqueado', pulse: false },
  error: { color: '#ff4d6d', label: 'Error', pulse: false },
  paused: { color: '#ffa940', label: 'Pausado', pulse: false },
}

const TABS = [
  { id: 'all', label: 'Todos' },
  { id: 'active', label: 'Activos' },
  { id: 'idle', label: 'Idle' },
  { id: 'blocked', label: 'Bloqueados' },
]

const EMPTY_FORM = {
  display_name: '',
  role: '',
  personality: '',
  avatar_icon: DEFAULT_AGENT_ICON,
  avatar_color: AGENT_AVATAR_COLORS[0],
  pixel_palette: PIXEL_AVATAR_PRESETS[0].palette,
  pixel_hue_shift: PIXEL_AVATAR_PRESETS[0].hueShift,
}

function agentColor(idx) { return AGENT_PALETTE[idx % AGENT_PALETTE.length] }
function agentStatus(state) { return STATUS_CONFIG[state] ?? STATUS_CONFIG.idle }
function roleIcon(role) {
  const key = Object.keys(ROLE_ICONS).find(k => role?.toLowerCase().includes(k))
  return ROLE_ICONS[key] ?? ROLE_ICONS.default
}
function getAvatarIcon(agent) {
  return AVATAR_ICONS[agent.avatar_icon] ?? roleIcon(agent.role)
}
function getAvatarColor(agent, idx) {
  return agent.avatar_color ?? agentColor(idx)
}

function AgentAvatar({ agent, idx, size = 40 }) {
  const color = getAvatarColor(agent, idx)
  const Icon = getAvatarIcon(agent)
  const st = agentStatus(agent.state)

  return (
    <div style={{ position: 'relative' }}>
      <div style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: `${Math.round(size * 0.28)}px`,
        background: `${color}18`,
        border: `1.5px solid ${color}35`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <Icon size={Math.round(size * 0.45)} style={{ color }} />
      </div>
      <div style={{
        position: 'absolute',
        bottom: '-2px',
        right: '-2px',
        width: `${Math.max(8, Math.round(size * 0.24))}px`,
        height: `${Math.max(8, Math.round(size * 0.24))}px`,
        borderRadius: '50%',
        background: st.color,
        border: '2px solid #0d0d12',
        ...(st.pulse ? { animation: 'pulse 2s infinite' } : {}),
      }} />
    </div>
  )
}

function PixelAvatarPreview({ palette }) {
  const frameWidth = 16
  const frameHeight = 32
  const spriteScale = 2
  const idleFrameX = 1 * frameWidth
  const downRowY = 0

  return (
    <div style={{
      width: '40px',
      height: '52px',
      overflow: 'hidden',
      borderRadius: '10px',
      background: 'linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))',
      border: '1px solid rgba(255,255,255,0.08)',
      flexShrink: 0,
    }}>
      <div
        style={{
          width: `${frameWidth * spriteScale}px`,
          height: `${frameHeight * spriteScale}px`,
          margin: '0 auto',
          marginTop: '2px',
          backgroundImage: `url('/pixel-assets/characters/char_${palette % 6}.png')`,
          backgroundPosition: `-${idleFrameX * spriteScale}px -${downRowY * spriteScale}px`,
          backgroundSize: `${112 * spriteScale}px ${96 * spriteScale}px`,
          backgroundRepeat: 'no-repeat',
          imageRendering: 'pixelated',
        }}
      />
    </div>
  )
}

function AgentModal({ open, onClose, onSubmit }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (open) {
      setForm(EMPTY_FORM)
      setSaved(false)
    }
  }, [open])

  if (!open) return null

  const CurrentIcon = AVATAR_ICONS[form.avatar_icon] ?? Bot
  const canSave = form.display_name.trim().length > 0

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function handleSubmit() {
    if (!canSave) return
    onSubmit(form)
    setSaved(true)
    setTimeout(() => {
      setSaved(false)
      onClose()
    }, 350)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={overlayStyle}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 8 }}
        transition={{ type: 'spring', stiffness: 360, damping: 28 }}
        style={modalStyle}
      >
        <div style={modalHeaderStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '38px', height: '38px', borderRadius: '10px',
              background: `${form.avatar_color}18`, border: `1.5px solid ${form.avatar_color}40`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <CurrentIcon size={18} style={{ color: form.avatar_color }} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-bright)' }}>Agregar agente</div>
              <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '1px' }}>Nombre, rol, avatar y personalidad base</div>
            </div>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>
            <X size={14} />
          </button>
        </div>

        <div style={modalBodyStyle}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: '14px',
            padding: '14px 16px', borderRadius: '10px', marginBottom: '20px',
            border: `1px solid ${form.avatar_color}30`, background: `${form.avatar_color}08`,
          }}>
            <div style={{
              width: '52px', height: '52px', borderRadius: '12px',
              background: `${form.avatar_color}20`, border: `2px solid ${form.avatar_color}50`,
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <CurrentIcon size={26} style={{ color: form.avatar_color }} />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '18px', color: 'var(--text-bright)' }}>
                {form.display_name.trim() || 'Nuevo agente'}
              </div>
              <div style={{ fontSize: '11px', color: form.avatar_color, marginTop: '2px', fontWeight: 600 }}>
                {form.role.trim() || 'Agent'}
              </div>
            </div>
          </div>

          <Field label="Nombre del agente">
            <input value={form.display_name} onChange={(e) => updateField('display_name', e.target.value)} placeholder="Ej. Emir" style={inputStyle} maxLength={32} />
          </Field>

          <Field label="Rol">
            <input value={form.role} onChange={(e) => updateField('role', e.target.value)} placeholder="Ej. Researcher, Developer, QA" style={inputStyle} maxLength={32} />
          </Field>

          <Field label="Personalidad">
            <textarea value={form.personality} onChange={(e) => updateField('personality', e.target.value)} placeholder="Describe cómo trabaja este agente" style={{ ...inputStyle, minHeight: '92px', resize: 'vertical' }} maxLength={140} />
          </Field>

          <Field label="Avatar">
            <div style={iconGridStyle}>
              {AVATAR_CHOICES.map((iconName) => {
                const Icon = AVATAR_ICONS[iconName]
                const active = form.avatar_icon === iconName
                return (
                  <button
                    key={iconName}
                    onClick={() => updateField('avatar_icon', iconName)}
                    style={{
                      ...iconBtnStyle,
                      background: active ? `${form.avatar_color}20` : 'transparent',
                      border: active ? `1px solid ${form.avatar_color}60` : '1px solid transparent',
                      color: active ? form.avatar_color : 'var(--muted)',
                    }}
                    title={iconName}
                  >
                    <Icon size={15} />
                  </button>
                )
              })}
            </div>
          </Field>

          <Field label="Color">
            <div style={colorGridStyle}>
              {AGENT_AVATAR_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => updateField('avatar_color', color)}
                  style={{
                    ...colorSwatchStyle,
                    background: color,
                    transform: form.avatar_color === color ? 'scale(1.15)' : 'scale(1)',
                    boxShadow: form.avatar_color === color ? `0 0 0 2px #0a0e1a, 0 0 0 4px ${color}` : 'none',
                  }}
                />
              ))}
            </div>
          </Field>

          <Field label="Avatar Pixel">
            <div style={pixelPresetGridStyle}>
              {PIXEL_AVATAR_PRESETS.map((preset, idx) => {
                const active =
                  form.pixel_palette === preset.palette &&
                  form.pixel_hue_shift === preset.hueShift
                return (
                  <button
                    key={`${preset.palette}-${preset.hueShift}`}
                    onClick={() => {
                      updateField('pixel_palette', preset.palette)
                      updateField('pixel_hue_shift', preset.hueShift)
                    }}
                    style={{
                      ...pixelPresetButtonStyle,
                      borderColor: active ? form.avatar_color : 'rgba(255,255,255,0.08)',
                      background: active ? `${form.avatar_color}14` : 'rgba(255,255,255,0.02)',
                    }}
                  >
                    <PixelAvatarPreview palette={preset.palette} />
                    <div style={{ textAlign: 'left', minWidth: 0 }}>
                      <div style={{ fontSize: '11px', color: 'var(--text)', fontWeight: 600 }}>{preset.label}</div>
                      <div style={{ fontSize: '10px', color: 'var(--muted)' }}>Skin #{preset.palette + 1}</div>
                    </div>
                  </button>
                )
              })}
            </div>
          </Field>
        </div>

        <div style={modalFooterStyle}>
          <button onClick={onClose} style={cancelBtnStyle}>Cancelar</button>
          <motion.button
            onClick={handleSubmit}
            disabled={!canSave}
            style={{
              ...saveBtnStyle,
              background: saved ? '#10b981' : form.avatar_color,
              opacity: canSave ? 1 : 0.5,
              boxShadow: `0 4px 14px ${form.avatar_color}40`,
            }}
            whileHover={canSave ? { scale: 1.02 } : undefined}
            whileTap={canSave ? { scale: 0.98 } : undefined}
          >
            {saved ? <Check size={13} /> : <Plus size={13} />}
            {saved ? 'Agregado' : 'Crear agente'}
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: '18px' }}>
      <label style={{ display: 'block', fontSize: '11px', fontWeight: 600, color: 'var(--muted)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '6px' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function AgentCard({ agent, idx, active, onClick }) {
  const color = getAvatarColor(agent, idx)
  const st = agentStatus(agent.state)

  return (
    <motion.div
      onClick={onClick}
      whileHover={{ y: -2, borderColor: `${color}40` }}
      style={{
        padding: '16px', borderRadius: '12px', cursor: 'pointer',
        background: active ? `${color}10` : 'rgba(255,255,255,0.02)',
        border: `1px solid ${active ? `${color}35` : 'rgba(255,255,255,0.06)'}`,
        transition: 'all 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '12px' }}>
        <AgentAvatar agent={agent} idx={idx} />
        <span style={{
          fontSize: '10px', fontWeight: 600, padding: '2px 7px', borderRadius: '20px',
          background: `${st.color}15`, color: st.color,
          border: `1px solid ${st.color}30`,
        }}>
          {st.label}
        </span>
      </div>

      <div style={{ fontWeight: 700, fontSize: '13px', color: 'var(--text-bright)', marginBottom: '2px' }}>
        {agent.display_name}
      </div>
      <div style={{ fontSize: '11px', color, marginBottom: '8px', fontWeight: 500 }}>
        {agent.role}
      </div>

      {agent.personality && (
        <p style={{ fontSize: '11px', color: 'var(--muted)', lineHeight: 1.5, margin: 0, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {agent.personality}
        </p>
      )}

      {agent.current_task && (
        <div style={{ marginTop: '10px', padding: '6px 8px', borderRadius: '6px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginBottom: '2px' }}>Tarea actual</div>
          <div style={{ fontSize: '11px', color: 'var(--text)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
            {agent.current_task}
          </div>
        </div>
      )}
    </motion.div>
  )
}

function AgentDetailModal({ agent, idx, tasks, onClose }) {
  const color = getAvatarColor(agent, idx)
  const st = agentStatus(agent.state)
  const agentTasks = tasks.filter(t => t.agent_id === agent.agent_id || t.assigned_to === agent.agent_id)
  const palette = agent.pixel_palette ?? 0

  // Large pixel sprite dimensions
  const frameW = 16, frameH = 32, scale = 4
  const idleFrameX = 1 * frameW

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={detailOverlayStyle}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 10 }}
        transition={{ type: 'spring', stiffness: 340, damping: 28 }}
        style={{ ...detailModalStyle, borderColor: `${color}25` }}
      >
        {/* ── Hero ── */}
        <div style={{ ...detailHeroStyle, background: `linear-gradient(160deg, ${color}12 0%, transparent 60%)` }}>
          {/* Close */}
          <button onClick={onClose} style={detailCloseBtnStyle}>
            <X size={14} />
          </button>

          {/* Pixel sprite — large centered */}
          <div style={pixelHeroWrapStyle}>
            <div style={{
              width: `${frameW * scale}px`,
              height: `${frameH * scale}px`,
              backgroundImage: `url('/pixel-assets/characters/char_${palette % 6}.png')`,
              backgroundPosition: `-${idleFrameX * scale}px 0px`,
              backgroundSize: `${112 * scale}px ${96 * scale}px`,
              backgroundRepeat: 'no-repeat',
              imageRendering: 'pixelated',
              filter: 'drop-shadow(0 8px 24px rgba(0,0,0,0.5))',
            }} />
            {/* Glow under feet */}
            <div style={{ width: '48px', height: '8px', borderRadius: '50%', background: color, opacity: 0.25, filter: 'blur(6px)', marginTop: '2px' }} />
          </div>

          {/* Name + role */}
          <div style={{ textAlign: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', marginBottom: '4px' }}>
              {/* Icon avatar */}
              <div style={{ width: '36px', height: '36px', borderRadius: '9px', background: `${color}20`, border: `1.5px solid ${color}40`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {(() => { const Icon = getAvatarIcon(agent); return <Icon size={17} style={{ color }} /> })()}
              </div>
              <div>
                <div style={{ fontWeight: 800, fontSize: '20px', color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
                  {agent.display_name}
                </div>
                <div style={{ fontSize: '12px', color, fontWeight: 600, marginTop: '1px' }}>
                  {agent.role}
                </div>
              </div>
            </div>

            {/* Status pill */}
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '20px', background: `${st.color}15`, border: `1px solid ${st.color}30`, marginTop: '6px' }}>
              <motion.div
                style={{ width: '6px', height: '6px', borderRadius: '50%', background: st.color }}
                animate={st.pulse ? { opacity: [1, 0.3, 1] } : {}}
                transition={{ duration: 1.4, repeat: Infinity }}
              />
              <span style={{ fontSize: '11px', fontWeight: 700, color: st.color, letterSpacing: '0.04em' }}>{st.label}</span>
            </div>
          </div>
        </div>

        {/* ── Body ── */}
        <div style={detailBodyStyle}>
          {/* Personality */}
          {agent.personality && (
            <DetailSection label="Personalidad" color={color}>
              <p style={{ fontSize: '13px', color: 'var(--muted)', lineHeight: 1.65, margin: 0 }}>{agent.personality}</p>
            </DetailSection>
          )}

          {/* Current task */}
          {agent.current_task && (
            <DetailSection label="Tarea activa" color={color}>
              <div style={{ padding: '10px 12px', borderRadius: '8px', background: `${color}0e`, border: `1px solid ${color}22`, fontSize: '13px', color: 'var(--text)', lineHeight: 1.5 }}>
                {agent.current_task}
              </div>
            </DetailSection>
          )}

          {/* Tasks */}
          {agentTasks.length > 0 && (
            <DetailSection label={`Tareas asignadas (${agentTasks.length})`} color={color}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {agentTasks.slice(0, 8).map(t => (
                  <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '9px', padding: '7px 10px', borderRadius: '7px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <TaskDot status={t.status} />
                    <span style={{ fontSize: '12px', color: 'var(--text)', flex: 1, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{t.title}</span>
                    <span style={{ fontSize: '10px', color: 'var(--muted)', flexShrink: 0 }}>{t.status}</span>
                  </div>
                ))}
              </div>
            </DetailSection>
          )}

          {/* Agent ID */}
          <DetailSection label="Identificador" color={color}>
            <div style={{ fontSize: '12px', color: 'var(--muted)', fontFamily: 'monospace', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', padding: '6px 10px', borderRadius: '6px' }}>
              {agent.agent_id}
            </div>
          </DetailSection>
        </div>
      </motion.div>
    </motion.div>
  )
}

function DetailSection({ label, color, children }) {
  return (
    <div style={{ marginBottom: '20px' }}>
      <div style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: color, opacity: 0.8, marginBottom: '8px' }}>
        {label}
      </div>
      {children}
    </div>
  )
}

function TaskDot({ status }) {
  const color = status === 'done' || status === 'completed' ? '#00d4a0'
    : status === 'running' || status === 'in_progress' ? '#8875ff'
    : status === 'blocked' || status === 'failed' ? '#ff4d6d'
    : 'rgba(255,255,255,0.2)'
  return <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: color, flexShrink: 0 }} />
}

const sectionLabel = {
  fontSize: '10px', fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: '8px',
}

function EmptyAgents({ onCreate }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: '14px', padding: '60px 0' }}>
      <div style={{ width: '56px', height: '56px', borderRadius: '14px', background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Bot size={24} style={{ color: '#38bdf8', opacity: 0.6 }} />
      </div>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-bright)', marginBottom: '4px' }}>Todavía no hay agentes configurados</div>
        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>Crea tu primer agente con nombre, rol y avatar personalizado.</div>
      </div>
      <button onClick={onCreate} style={createBtnStyle}>
        <Plus size={13} />
        Agregar primer agente
      </button>
    </div>
  )
}

export function AgentsView({ agents, tasks, onCreateAgent }) {
  const [tab, setTab] = useState('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const [viewMode, setViewMode] = useState('grid')
  const [showCreate, setShowCreate] = useState(false)

  useEffect(() => {
    if (agents.length === 0) {
      setShowCreate(true)
    }
  }, [agents.length])

  const filtered = useMemo(() => {
    return agents.filter(a => {
      if (tab === 'active' && a.state !== 'running' && a.state !== 'active' && a.state !== 'working') return false
      if (tab === 'idle' && a.state !== 'idle') return false
      if (tab === 'blocked' && a.state !== 'blocked') return false
      if (search && !a.display_name?.toLowerCase().includes(search.toLowerCase()) && !a.role?.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [agents, tab, search])

  const tabCounts = useMemo(() => ({
    all: agents.length,
    active: agents.filter(a => a.state !== 'idle').length,
    idle: agents.filter(a => a.state === 'idle').length,
    blocked: agents.filter(a => a.state === 'blocked').length,
  }), [agents])

  const selectedIdx = selected ? agents.findIndex(a => a.agent_id === selected.agent_id) : -1

  function handleCreateAgent(form) {
    onCreateAgent?.(form)
    setShowCreate(false)
  }

  return (
    <div className="view-shell">
      <div className="view-header">
        <div>
          <h1 className="view-title">Agentes</h1>
          <p className="view-subtitle">Equipo de {agents.length} agentes — {agents.filter(a => a.state !== 'idle').length} activos ahora.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={() => setViewMode('grid')} style={{ ...iconBtn, background: viewMode === 'grid' ? 'rgba(136,117,255,0.2)' : 'transparent', color: viewMode === 'grid' ? '#a899ff' : 'var(--muted)' }}>
            <GitBranch size={13} />
          </button>
          <button onClick={() => setViewMode('list')} style={{ ...iconBtn, background: viewMode === 'list' ? 'rgba(136,117,255,0.2)' : 'transparent', color: viewMode === 'list' ? '#a899ff' : 'var(--muted)' }}>
            <List size={13} />
          </button>
          <button onClick={() => setShowCreate(true)} style={createBtnStyle}>
            <Plus size={13} />
            Agregar agente
          </button>
        </div>
      </div>

      <div style={filterBar}>
        <div style={{ display: 'flex', gap: '2px', background: 'rgba(255,255,255,0.04)', padding: '3px', borderRadius: '8px' }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              ...tabBtn,
              background: tab === t.id ? 'rgba(136,117,255,0.2)' : 'transparent',
              color: tab === t.id ? '#a899ff' : 'var(--muted)',
            }}>
              {t.label}
              {tabCounts[t.id] > 0 && (
                <span style={{ ...countBadge, background: tab === t.id ? 'rgba(136,117,255,0.3)' : 'rgba(255,255,255,0.08)' }}>
                  {tabCounts[t.id]}
                </span>
              )}
            </button>
          ))}
        </div>
        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <Search size={12} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar agente..." style={searchInput} />
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'hidden', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ height: '100%', overflowY: 'auto', padding: filtered.length === 0 ? '0' : '16px', background: 'rgba(255,255,255,0.01)' }}>
          {filtered.length === 0 ? (
            <EmptyAgents onCreate={() => setShowCreate(true)} />
          ) : viewMode === 'grid' ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '12px' }}>
              {filtered.map((a) => (
                <AgentCard
                  key={a.agent_id}
                  agent={a}
                  idx={agents.indexOf(a)}
                  active={selected?.agent_id === a.agent_id}
                  onClick={() => setSelected(a)}
                />
              ))}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {filtered.map((a) => (
                <AgentListRow
                  key={a.agent_id}
                  agent={a}
                  idx={agents.indexOf(a)}
                  active={selected?.agent_id === a.agent_id}
                  onClick={() => setSelected(a)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Agent detail modal */}
      <AnimatePresence>
        {selected && (
          <AgentDetailModal
            agent={selected}
            idx={selectedIdx}
            tasks={tasks}
            onClose={() => setSelected(null)}
          />
        )}
      </AnimatePresence>

      {/* Create agent modal */}
      <AnimatePresence>
        {showCreate && (
          <AgentModal
            open={showCreate}
            onClose={() => setShowCreate(false)}
            onSubmit={handleCreateAgent}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

function AgentListRow({ agent, idx, active, onClick }) {
  const color = getAvatarColor(agent, idx)
  const st = agentStatus(agent.state)

  return (
    <motion.div
      onClick={onClick}
      whileHover={{ background: 'rgba(255,255,255,0.04)' }}
      style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        padding: '10px 14px', cursor: 'pointer', borderRadius: '8px',
        background: active ? `${color}0a` : 'transparent',
        borderLeft: active ? `2px solid ${color}` : '2px solid transparent',
        transition: 'all 0.12s',
      }}
    >
      <AgentAvatar agent={agent} idx={idx} size={32} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-bright)' }}>{agent.display_name}</div>
        <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{agent.role}</div>
      </div>
      {agent.current_task && (
        <div style={{ fontSize: '11px', color: 'var(--muted)', maxWidth: '200px', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
          {agent.current_task}
        </div>
      )}
      <span style={{ fontSize: '10px', fontWeight: 600, padding: '2px 7px', borderRadius: '20px', background: `${st.color}15`, color: st.color, border: `1px solid ${st.color}30`, flexShrink: 0 }}>
        {st.label}
      </span>
    </motion.div>
  )
}

const filterBar = { display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }
const tabBtn = { padding: '4px 10px', borderRadius: '5px', border: 'none', cursor: 'pointer', fontSize: '12px', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '5px', fontFamily: 'Inter, system-ui, sans-serif', transition: 'all 0.12s' }
const countBadge = { fontSize: '10px', fontWeight: 700, padding: '0 5px', borderRadius: '8px', minWidth: '16px', textAlign: 'center' }
const searchInput = { paddingLeft: '28px', paddingRight: '10px', paddingTop: '6px', paddingBottom: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '7px', color: 'var(--text)', fontSize: '12px', fontFamily: 'Inter, system-ui, sans-serif', outline: 'none', width: '180px' }
const iconBtn = { width: '30px', height: '30px', borderRadius: '7px', border: '1px solid rgba(255,255,255,0.08)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Inter, system-ui, sans-serif', transition: 'all 0.12s' }
const createBtnStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  padding: '8px 12px',
  borderRadius: '8px',
  border: '1px solid rgba(0,212,160,0.2)',
  background: 'rgba(0,212,160,0.12)',
  color: '#00d4a0',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer',
  fontFamily: 'Inter, system-ui, sans-serif',
}
const overlayStyle = {
  position: 'fixed', inset: 0, zIndex: 1000,
  background: 'rgba(0, 0, 0, 0.65)', backdropFilter: 'blur(4px)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}
const modalStyle = {
  width: '460px', maxWidth: '95vw', maxHeight: '90vh',
  background: '#0c1123',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '16px',
  boxShadow: '0 24px 60px rgba(0,0,0,0.6)',
  display: 'flex', flexDirection: 'column', overflow: 'hidden',
}
const modalHeaderStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '16px 18px', borderBottom: '1px solid rgba(255,255,255,0.06)', flexShrink: 0,
}
const modalBodyStyle = { padding: '20px 18px', overflowY: 'auto', flex: 1 }
const modalFooterStyle = {
  display: 'flex', gap: '8px', justifyContent: 'flex-end',
  padding: '14px 18px', borderTop: '1px solid rgba(255,255,255,0.06)', flexShrink: 0,
}
const closeBtnStyle = {
  background: 'transparent', border: 'none', cursor: 'pointer',
  color: 'var(--muted)', padding: '6px', borderRadius: '6px',
  display: 'flex', alignItems: 'center',
}
const inputStyle = {
  width: '100%', background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', padding: '9px 12px',
  color: 'var(--text)', fontSize: '13px', outline: 'none', fontFamily: 'Inter, system-ui, sans-serif',
}
const iconGridStyle = {
  display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)',
  gap: '4px', maxHeight: '180px', overflowY: 'auto', padding: '2px',
}
const iconBtnStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: '34px', height: '34px', borderRadius: '7px', cursor: 'pointer',
  transition: 'all 0.12s',
}
const colorGridStyle = { display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)', gap: '8px' }
const pixelPresetGridStyle = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }
const colorSwatchStyle = {
  width: '28px', height: '28px', borderRadius: '50%', border: 'none',
  cursor: 'pointer', transition: 'transform 0.15s, box-shadow 0.15s',
}
const pixelPresetButtonStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  padding: '10px',
  borderRadius: '10px',
  border: '1px solid rgba(255,255,255,0.08)',
  cursor: 'pointer',
  color: 'var(--text)',
}
const cancelBtnStyle = {
  background: 'transparent', border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '8px', padding: '8px 16px', color: 'var(--muted)',
  fontSize: '12px', cursor: 'pointer', fontFamily: 'Inter, system-ui, sans-serif',
}
const saveBtnStyle = {
  border: 'none', borderRadius: '8px', padding: '8px 18px',
  color: '#fff', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
  display: 'flex', alignItems: 'center', gap: '6px', fontFamily: 'Inter, system-ui, sans-serif',
}

// ── Agent detail modal styles ────────────────────────────────────
const detailOverlayStyle = {
  position: 'fixed', inset: 0, zIndex: 1000,
  background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(6px)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}
const detailModalStyle = {
  width: '480px', maxWidth: '95vw', maxHeight: '88vh',
  background: 'linear-gradient(160deg, #0d1020 0%, #0a0d1c 100%)',
  border: '1px solid',
  borderRadius: '20px',
  boxShadow: '0 32px 80px rgba(0,0,0,0.7)',
  display: 'flex', flexDirection: 'column', overflow: 'hidden',
}
const detailHeroStyle = {
  padding: '28px 24px 24px',
  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px',
  borderBottom: '1px solid rgba(255,255,255,0.06)',
  position: 'relative', flexShrink: 0,
}
const detailCloseBtnStyle = {
  position: 'absolute', top: '14px', right: '14px',
  background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '7px', cursor: 'pointer', color: 'var(--muted)',
  width: '28px', height: '28px', display: 'flex', alignItems: 'center', justifyContent: 'center',
}
const pixelHeroWrapStyle = {
  display: 'flex', flexDirection: 'column', alignItems: 'center',
  filter: 'drop-shadow(0 4px 16px rgba(0,0,0,0.4))',
}
const detailBodyStyle = {
  padding: '22px 24px', overflowY: 'auto', flex: 1,
}
