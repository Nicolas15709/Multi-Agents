import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X, Check, Building2, Home, Cpu, Globe, Star, Zap, Shield, Rocket,
  Brain, Bot, Layers, Target, Code2, Terminal, Paintbrush, Search,
  Activity, Wifi, Coffee, Music, Camera, Smile, Heart, Flame,
  TreePine, Mountain, Sun, Moon, Cloud, Sparkles, Crown, Swords,
  Briefcase, BookOpen, FlaskConical, Microscope, Satellite, Landmark,
} from 'lucide-react'

const OFFICE_ICONS = [
  { name: 'building', Icon: Building2 },
  { name: 'home', Icon: Home },
  { name: 'cpu', Icon: Cpu },
  { name: 'globe', Icon: Globe },
  { name: 'star', Icon: Star },
  { name: 'zap', Icon: Zap },
  { name: 'shield', Icon: Shield },
  { name: 'rocket', Icon: Rocket },
  { name: 'brain', Icon: Brain },
  { name: 'bot', Icon: Bot },
  { name: 'layers', Icon: Layers },
  { name: 'target', Icon: Target },
  { name: 'code', Icon: Code2 },
  { name: 'terminal', Icon: Terminal },
  { name: 'paint', Icon: Paintbrush },
  { name: 'search', Icon: Search },
  { name: 'activity', Icon: Activity },
  { name: 'wifi', Icon: Wifi },
  { name: 'coffee', Icon: Coffee },
  { name: 'music', Icon: Music },
  { name: 'camera', Icon: Camera },
  { name: 'smile', Icon: Smile },
  { name: 'heart', Icon: Heart },
  { name: 'flame', Icon: Flame },
  { name: 'tree', Icon: TreePine },
  { name: 'mountain', Icon: Mountain },
  { name: 'sun', Icon: Sun },
  { name: 'moon', Icon: Moon },
  { name: 'cloud', Icon: Cloud },
  { name: 'sparkles', Icon: Sparkles },
  { name: 'crown', Icon: Crown },
  { name: 'swords', Icon: Swords },
  { name: 'briefcase', Icon: Briefcase },
  { name: 'book', Icon: BookOpen },
  { name: 'flask', Icon: FlaskConical },
  { name: 'microscope', Icon: Microscope },
  { name: 'satellite', Icon: Satellite },
  { name: 'landmark', Icon: Landmark },
]

const BRAND_COLORS = [
  '#6366f1', '#8b5cf6', '#a855f7', '#ec4899',
  '#ef4444', '#f97316', '#f59e0b', '#eab308',
  '#22c55e', '#10b981', '#14b8a6', '#06b6d4',
  '#3b82f6', '#0ea5e9', '#64748b', '#94a3b8',
]

const STORAGE_KEY = 'missioncontrol.office'

export function loadOfficeConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return { name: 'Virtual Agency HQ', description: '', icon: 'building', color: '#6366f1' }
}

export function saveOfficeConfig(cfg) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)) } catch {}
}

export function OfficeCustomizer({ config, onSave, onClose }) {
  const [name, setName] = useState(config.name)
  const [description, setDescription] = useState(config.description ?? '')
  const [icon, setIcon] = useState(config.icon)
  const [color, setColor] = useState(config.color)
  const [iconSearch, setIconSearch] = useState('')
  const [saved, setSaved] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const filteredIcons = iconSearch
    ? OFFICE_ICONS.filter(i => i.name.includes(iconSearch.toLowerCase()))
    : OFFICE_ICONS

  const CurrentIcon = OFFICE_ICONS.find(i => i.name === icon)?.Icon ?? Building2

  function handleSave() {
    const cfg = { name: name.trim() || 'Mi Oficina', description, icon, color }
    saveOfficeConfig(cfg)
    onSave(cfg)
    setSaved(true)
    setTimeout(() => { setSaved(false); onClose() }, 800)
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={overlayStyle}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 8 }}
        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
        style={modalStyle}
      >
        {/* Header */}
        <div style={modalHeaderStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ ...iconPreviewStyle, background: `${color}20`, border: `1px solid ${color}40` }}>
              <CurrentIcon size={18} style={{ color }} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-bright)' }}>Personalizar Oficina</div>
              <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '1px' }}>Nombre, avatar y estilo</div>
            </div>
          </div>
          <button onClick={onClose} style={closeBtnStyle}>
            <X size={14} />
          </button>
        </div>

        <div style={modalBodyStyle}>
          {/* Preview strip */}
          <div style={{ ...previewStripStyle, borderColor: `${color}30`, background: `${color}08` }}>
            <div style={{ ...bigIconStyle, background: `${color}20`, border: `2px solid ${color}50` }}>
              <CurrentIcon size={28} style={{ color }} />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '18px', color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
                {name || 'Mi Oficina'}
              </div>
              {description && (
                <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px' }}>{description}</div>
              )}
            </div>
          </div>

          {/* Office Name */}
          <Field label="Nombre de la Oficina">
            <input
              ref={inputRef}
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Mi Oficina HQ"
              maxLength={40}
              style={inputStyle}
              onFocus={e => e.target.style.borderColor = color}
              onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
            />
          </Field>

          {/* Description */}
          <Field label="DescripciÃ³n (opcional)">
            <input
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="El centro de operaciones de mi equipo de agentes"
              maxLength={80}
              style={inputStyle}
              onFocus={e => e.target.style.borderColor = color}
              onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
            />
          </Field>

          {/* Icon Picker */}
          <Field label="Ãcono">
            <div style={{ marginBottom: '8px' }}>
              <input
                value={iconSearch}
                onChange={e => setIconSearch(e.target.value)}
                placeholder="Buscar Ã­cono..."
                style={{ ...inputStyle, fontSize: '11px', height: '30px' }}
              />
            </div>
            <div style={iconGridStyle}>
              {filteredIcons.map(({ name: n, Icon }) => (
                <button
                  key={n}
                  title={n}
                  onClick={() => setIcon(n)}
                  style={{
                    ...iconBtnStyle,
                    background: icon === n ? `${color}20` : 'transparent',
                    border: icon === n ? `1px solid ${color}60` : '1px solid transparent',
                    color: icon === n ? color : 'var(--muted)',
                  }}
                >
                  <Icon size={15} />
                </button>
              ))}
              {filteredIcons.length === 0 && (
                <div style={{ gridColumn: '1/-1', textAlign: 'center', fontSize: '11px', color: 'var(--muted)', padding: '12px' }}>
                  Sin resultados
                </div>
              )}
            </div>
          </Field>

          {/* Color Picker */}
          <Field label="Color de marca">
            <div style={colorGridStyle}>
              {BRAND_COLORS.map(c => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  style={{
                    ...colorSwatchStyle,
                    background: c,
                    transform: color === c ? 'scale(1.15)' : 'scale(1)',
                    boxShadow: color === c ? `0 0 0 2px #0a0e1a, 0 0 0 4px ${c}` : 'none',
                  }}
                  title={c}
                />
              ))}
            </div>
          </Field>
        </div>

        {/* Footer */}
        <div style={modalFooterStyle}>
          <button onClick={onClose} style={cancelBtnStyle}>Cancelar</button>
          <motion.button
            onClick={handleSave}
            style={{ ...saveBtnStyle, background: saved ? '#10b981' : color, boxShadow: `0 4px 14px ${color}40` }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {saved ? <Check size={13} /> : null}
            {saved ? 'Guardado' : 'Guardar cambios'}
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

// â”€â”€ Styles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const overlayStyle = {
  position: 'fixed', inset: 0, zIndex: 1000,
  background: 'rgba(0, 0, 0, 0.65)',
  backdropFilter: 'blur(4px)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}
const modalStyle = {
  width: '440px', maxWidth: '95vw', maxHeight: '90vh',
  background: '#0c1123',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '16px',
  boxShadow: '0 24px 60px rgba(0,0,0,0.6)',
  display: 'flex', flexDirection: 'column',
  overflow: 'hidden',
}
const modalHeaderStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  padding: '16px 18px',
  borderBottom: '1px solid rgba(255,255,255,0.06)',
  flexShrink: 0,
}
const modalBodyStyle = {
  padding: '20px 18px',
  overflowY: 'auto',
  flex: 1,
}
const modalFooterStyle = {
  display: 'flex', gap: '8px', justifyContent: 'flex-end',
  padding: '14px 18px',
  borderTop: '1px solid rgba(255,255,255,0.06)',
  flexShrink: 0,
}
const iconPreviewStyle = {
  width: '34px', height: '34px', borderRadius: '8px',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}
const closeBtnStyle = {
  background: 'transparent', border: 'none', cursor: 'pointer',
  color: 'var(--muted)', padding: '6px',
  borderRadius: '6px', display: 'flex', alignItems: 'center',
  transition: 'background 0.15s',
}
const previewStripStyle = {
  display: 'flex', alignItems: 'center', gap: '14px',
  padding: '14px 16px', borderRadius: '10px',
  border: '1px solid', marginBottom: '22px',
}
const bigIconStyle = {
  width: '52px', height: '52px', borderRadius: '12px',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  flexShrink: 0,
}
const inputStyle = {
  width: '100%', background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '8px', padding: '9px 12px',
  color: 'var(--text)', fontSize: '13px', outline: 'none',
  transition: 'border-color 0.15s',
  fontFamily: 'Inter, system-ui, sans-serif',
}
const iconGridStyle = {
  display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)',
  gap: '4px', maxHeight: '160px', overflowY: 'auto',
  padding: '2px',
}
const iconBtnStyle = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: '34px', height: '34px', borderRadius: '7px',
  cursor: 'pointer', transition: 'all 0.12s',
}
const colorGridStyle = {
  display: 'grid', gridTemplateColumns: 'repeat(8, 1fr)',
  gap: '8px',
}
const colorSwatchStyle = {
  width: '28px', height: '28px', borderRadius: '50%',
  border: 'none', cursor: 'pointer',
  transition: 'transform 0.15s, box-shadow 0.15s',
}
const cancelBtnStyle = {
  background: 'transparent', border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: '8px', padding: '8px 16px',
  color: 'var(--muted)', fontSize: '12px', cursor: 'pointer',
  fontFamily: 'Inter, system-ui, sans-serif',
}
const saveBtnStyle = {
  border: 'none', borderRadius: '8px', padding: '8px 18px',
  color: '#fff', fontSize: '12px', fontWeight: 600, cursor: 'pointer',
  display: 'flex', alignItems: 'center', gap: '6px',
  transition: 'background 0.2s',
  fontFamily: 'Inter, system-ui, sans-serif',
}

