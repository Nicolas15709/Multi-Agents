import { motion } from 'framer-motion'
import {
  Building2, Home, Cpu, Globe, Star, Zap, Shield, Rocket,
  Brain, Bot, Layers, Target, Code2, Terminal, Paintbrush, Search,
  Activity, Wifi, Coffee, Music, Camera, Smile, Heart, Flame,
  TreePine, Mountain, Sun, Moon, Cloud, Sparkles, Crown, Swords,
  Briefcase, BookOpen, FlaskConical, Microscope, Satellite, Landmark,
  Settings2,
} from 'lucide-react'

const ICON_MAP = {
  building: Building2, home: Home, cpu: Cpu, globe: Globe,
  star: Star, zap: Zap, shield: Shield, rocket: Rocket,
  brain: Brain, bot: Bot, layers: Layers, target: Target,
  code: Code2, terminal: Terminal, paint: Paintbrush, search: Search,
  activity: Activity, wifi: Wifi, coffee: Coffee, music: Music,
  camera: Camera, smile: Smile, heart: Heart, flame: Flame,
  tree: TreePine, mountain: Mountain, sun: Sun, moon: Moon,
  cloud: Cloud, sparkles: Sparkles, crown: Crown, swords: Swords,
  briefcase: Briefcase, book: BookOpen, flask: FlaskConical,
  microscope: Microscope, satellite: Satellite, landmark: Landmark,
}

export function OfficeIdentity({ config, onOpenCustomizer }) {
  const { name, description, icon, color } = config
  const Icon = ICON_MAP[icon] ?? Building2

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.4 }}
      style={containerStyle}
    >
      {/* Avatar */}
      <motion.div
        style={{ ...avatarStyle, background: `${color}18`, border: `1.5px solid ${color}40` }}
        whileHover={{ scale: 1.05 }}
      >
        <Icon size={18} style={{ color }} />
        {/* Glow */}
        <div style={{ ...glowStyle, background: color }} />
      </motion.div>

      {/* Name + description */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 800, fontSize: '13px', color: 'var(--text-bright)', letterSpacing: '-0.01em', lineHeight: 1 }}>
          {name}
        </div>
        {description && (
          <div style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {description}
          </div>
        )}
      </div>

      {/* Color dot */}
      <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: color, flexShrink: 0, boxShadow: `0 0 6px ${color}` }} />

      {/* Settings button */}
      <motion.button
        onClick={onOpenCustomizer}
        style={settingsBtnStyle}
        whileHover={{ scale: 1.1, color: 'var(--text)' }}
        whileTap={{ scale: 0.95 }}
        title="Personalizar oficina"
      >
        <Settings2 size={12} />
      </motion.button>
    </motion.div>
  )
}

const containerStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '7px 10px',
  background: 'rgba(12, 17, 35, 0.7)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: '10px',
  backdropFilter: 'blur(10px)',
  maxWidth: '100%',
  overflow: 'hidden',
}

const avatarStyle = {
  width: '32px',
  height: '32px',
  borderRadius: '8px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  position: 'relative',
  flexShrink: 0,
  overflow: 'hidden',
}

const glowStyle = {
  position: 'absolute',
  inset: 0,
  borderRadius: '8px',
  opacity: 0.08,
  pointerEvents: 'none',
}

const settingsBtnStyle = {
  background: 'transparent',
  border: 'none',
  cursor: 'pointer',
  color: 'var(--muted)',
  padding: '4px',
  display: 'flex',
  alignItems: 'center',
  borderRadius: '5px',
  flexShrink: 0,
  transition: 'color 0.15s',
}
