import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Code2, Rocket, AlertCircle, BookOpen, Shield, Search,
  BarChart3, TrendingUp, FileText, Globe, Target, RefreshCw,
  Microscope, Eye, Flame, ChevronRight, Play, X, Zap, Workflow,
} from 'lucide-react'

const TEMPLATES = [
  {
    id: 'general_operating_request', cat: 'general', icon: Workflow, color: '#60a5fa',
    label: 'Open Operating Request', desc: 'Entrega un objetivo abierto y deja que el team lead clasifique el caso, arme el graph de trabajo y proponga especialistas.',
    agents: ['Lead', 'Research', 'Build', 'Review', 'Dynamic Specialists'],
    duration: 'Variable', complexity: 'Abierta',
  },
  // Desarrollo / producto
  {
    id: 'software_build',       cat: 'development', icon: Code2,      color: '#8875ff',
    label: 'Software Build',    desc: 'Construye una aplicación o feature desde cero con el equipo completo.',
    agents: ['Supervisor', 'Researcher', 'Designer', 'Developer', 'QA'],
    duration: '2-8h', complexity: 'Alta',
  },
  {
    id: 'prototype_to_build',   cat: 'development', icon: Rocket,     color: '#8b5cf6',
    label: 'Prototype → Build', desc: 'Convierte un prototipo o spec en código funcional y testeado.',
    agents: ['Designer', 'Developer', 'QA'],
    duration: '1-4h', complexity: 'Media',
  },
  {
    id: 'landing_launch',       cat: 'development', icon: Globe,      color: '#38bdf8',
    label: 'Landing Launch',    desc: 'Diseña e implementa una landing page optimizada para conversión.',
    agents: ['Designer', 'Developer'],
    duration: '1-3h', complexity: 'Media',
  },
  {
    id: 'feature_extension',    cat: 'development', icon: Zap,        color: '#a899ff',
    label: 'Feature Extension', desc: 'Extiende una funcionalidad existente con nuevas capacidades.',
    agents: ['Developer', 'QA'],
    duration: '30min-2h', complexity: 'Baja-Media',
  },
  {
    id: 'bugfix_debug',         cat: 'development', icon: AlertCircle,color: '#ffa940',
    label: 'Bugfix & Debug',    desc: 'Investigación y resolución de bugs o comportamientos inesperados.',
    agents: ['Developer', 'QA'],
    duration: '15min-2h', complexity: 'Variable',
  },
  {
    id: 'documentation_pack',   cat: 'development', icon: BookOpen,   color: '#00d4a0',
    label: 'Documentation Pack',desc: 'Genera documentación técnica, READMEs, wikis y guías de uso.',
    agents: ['Researcher', 'Developer'],
    duration: '1-3h', complexity: 'Baja',
  },
  // Seguridad / calidad
  {
    id: 'security_review',      cat: 'security',    icon: Shield,     color: '#ff4d6d',
    label: 'Security Review',   desc: 'Auditoría de seguridad: OWASP Top 10, secretos expuestos, permisos.',
    agents: ['Researcher', 'Developer', 'QA'],
    duration: '1-4h', complexity: 'Alta',
  },
  {
    id: 'qa_hardening',         cat: 'security',    icon: Shield,     color: '#f97316',
    label: 'QA Hardening',      desc: 'Suite de pruebas exhaustiva: unit, integration, edge cases.',
    agents: ['QA', 'Developer'],
    duration: '1-3h', complexity: 'Media',
  },
  {
    id: 'post_build_audit',     cat: 'security',    icon: Eye,        color: '#fbbf24',
    label: 'Post-Build Audit',  desc: 'Revisión post-lanzamiento: performance, seguridad, accesibilidad.',
    agents: ['Researcher', 'QA'],
    duration: '1-2h', complexity: 'Media',
  },
  // Marketing / marca
  {
    id: 'marketing_campaign',   cat: 'marketing',   icon: BarChart3,  color: '#ec4899',
    label: 'Marketing Campaign',desc: 'Diseña y ejecuta una campaña completa de marketing digital.',
    agents: ['Researcher', 'Designer'],
    duration: '2-6h', complexity: 'Media-Alta',
  },
  {
    id: 'brand_growth',         cat: 'marketing',   icon: TrendingUp, color: '#f472b6',
    label: 'Brand Growth',      desc: 'Estrategia de crecimiento de marca y presencia digital.',
    agents: ['Researcher', 'Designer'],
    duration: '2-4h', complexity: 'Media',
  },
  {
    id: 'content_engine',       cat: 'marketing',   icon: FileText,   color: '#a78bfa',
    label: 'Content Engine',    desc: 'Genera contenido masivo: posts, copys, emails, artículos.',
    agents: ['Researcher', 'Designer'],
    duration: '1-4h', complexity: 'Baja-Media',
  },
  {
    id: 'social_presence_audit',cat: 'marketing',   icon: Globe,      color: '#c084fc',
    label: 'Social Audit',      desc: 'Análisis de presencia social, competencia y oportunidades.',
    agents: ['Researcher'],
    duration: '1-2h', complexity: 'Baja',
  },
  // Negocio / prospección
  {
    id: 'business_audit_proposal', cat: 'business', icon: Target,     color: '#34d399',
    label: 'Business Audit',    desc: 'Diagnóstico del negocio y generación de propuesta de mejora.',
    agents: ['Supervisor', 'Researcher'],
    duration: '2-5h', complexity: 'Alta',
  },
  {
    id: 'competitor_intelligence',  cat: 'business', icon: Microscope,color: '#6ee7b7',
    label: 'Competitor Intel',  desc: 'Análisis profundo de competidores, precios y posicionamiento.',
    agents: ['Researcher'],
    duration: '1-3h', complexity: 'Media',
  },
  {
    id: 'offer_design',             cat: 'business', icon: Flame,      color: '#a7f3d0',
    label: 'Offer Design',      desc: 'Diseña una oferta irresistible con propuesta de valor clara.',
    agents: ['Researcher', 'Designer'],
    duration: '1-2h', complexity: 'Media',
  },
  // Investigación / operación
  {
    id: 'research_only',         cat: 'research',   icon: Microscope, color: '#67e8f9',
    label: 'Research Only',     desc: 'Investigación profunda sobre un tema, tecnología o mercado.',
    agents: ['Researcher'],
    duration: '30min-3h', complexity: 'Variable',
  },
  {
    id: 'monitor_and_report',    cat: 'research',   icon: Eye,        color: '#7dd3fc',
    label: 'Monitor & Report',  desc: 'Monitoreo continuo de métricas, alertas y generación de reporte.',
    agents: ['Researcher', 'Supervisor'],
    duration: 'Continuo', complexity: 'Baja',
  },
  {
    id: 'maintenance_cycle',     cat: 'research',   icon: RefreshCw,  color: '#93c5fd',
    label: 'Maintenance Cycle', desc: 'Ciclo de mantenimiento: limpieza, actualización y health check.',
    agents: ['Developer', 'QA'],
    duration: '30min-2h', complexity: 'Baja',
  },
]

const CATEGORIES = [
  { id: 'all',         label: 'Todas',        count: TEMPLATES.length },
  { id: 'general',     label: 'Abierta',      count: TEMPLATES.filter(t => t.cat === 'general').length },
  { id: 'development', label: 'Desarrollo',   count: TEMPLATES.filter(t => t.cat === 'development').length },
  { id: 'security',    label: 'Seguridad',    count: TEMPLATES.filter(t => t.cat === 'security').length },
  { id: 'marketing',   label: 'Marketing',    count: TEMPLATES.filter(t => t.cat === 'marketing').length },
  { id: 'business',    label: 'Negocio',      count: TEMPLATES.filter(t => t.cat === 'business').length },
  { id: 'research',    label: 'Investigación',count: TEMPLATES.filter(t => t.cat === 'research').length },
]

const CAT_LABELS = {
  general: 'Abierta',
  development: 'Desarrollo',
  security: 'Seguridad',
  marketing: 'Marketing',
  business: 'Negocio',
  research: 'Investigación',
}

function TemplateCard({ tpl, onLaunch, onSelect, active }) {
  return (
    <motion.div
      whileHover={{ y: -2, borderColor: `${tpl.color}40` }}
      onClick={() => onSelect(active ? null : tpl)}
      style={{
        padding: '16px', borderRadius: '12px', cursor: 'pointer',
        background: active ? `${tpl.color}08` : 'rgba(255,255,255,0.02)',
        border: `1px solid ${active ? `${tpl.color}30` : 'rgba(255,255,255,0.06)'}`,
        display: 'flex', flexDirection: 'column', gap: '10px',
        transition: 'all 0.15s',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{
          width: '36px', height: '36px', borderRadius: '9px',
          background: `${tpl.color}14`, border: `1px solid ${tpl.color}28`,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <tpl.icon size={17} style={{ color: tpl.color }} />
        </div>
        <span style={{ fontSize: '10px', color: 'var(--muted)', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px' }}>
          {tpl.duration}
        </span>
      </div>

      <div>
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-bright)', marginBottom: '4px' }}>{tpl.label}</div>
        <p style={{ fontSize: '11px', color: 'var(--muted)', lineHeight: 1.5, margin: 0, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {tpl.desc}
        </p>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap' }}>
          {tpl.agents.slice(0, 3).map(a => (
            <span key={a} style={{ fontSize: '9px', color: 'var(--muted)', background: 'rgba(255,255,255,0.06)', padding: '1px 5px', borderRadius: '3px' }}>{a}</span>
          ))}
          {tpl.agents.length > 3 && <span style={{ fontSize: '9px', color: 'var(--muted)' }}>+{tpl.agents.length - 3}</span>}
        </div>
        <button
          onClick={e => { e.stopPropagation(); onLaunch(tpl) }}
          style={{
            display: 'flex', alignItems: 'center', gap: '4px',
            padding: '4px 10px', borderRadius: '6px', border: `1px solid ${tpl.color}30`,
            background: `${tpl.color}12`, color: tpl.color,
            fontSize: '11px', fontWeight: 600, cursor: 'pointer',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          <Play size={9} fill="currentColor" />
          Usar
        </button>
      </div>
    </motion.div>
  )
}

function TemplateDetail({ tpl, onLaunch, onClose }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.2 }}
      style={{
        width: '300px', flexShrink: 0, borderLeft: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden',
      }}
    >
      <div style={{ padding: '16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
        <div style={{ width: '36px', height: '36px', borderRadius: '9px', background: `${tpl.color}14`, border: `1px solid ${tpl.color}28`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
          <tpl.icon size={17} style={{ color: tpl.color }} />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-bright)' }}>{tpl.label}</div>
          <div style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '2px' }}>{CAT_LABELS[tpl.cat] ?? tpl.cat}</div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: '2px' }}>
          <X size={14} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <div style={sectionLabel}>Descripción</div>
          <p style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.6, margin: 0 }}>{tpl.desc}</p>
        </div>
        <div>
          <div style={sectionLabel}>Agentes involucrados</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {tpl.agents.map(a => (
              <div key={a} style={{ fontSize: '12px', color: 'var(--text)', padding: '6px 8px', borderRadius: '6px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                {a}
              </div>
            ))}
          </div>
        </div>
        <div>
          <div style={sectionLabel}>Detalles</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <MetaRow label="Duración estimada" value={tpl.duration} />
            <MetaRow label="Complejidad" value={tpl.complexity} />
            <MetaRow label="ID" value={tpl.id} />
          </div>
        </div>
      </div>

      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <button
          onClick={() => onLaunch(tpl)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
            padding: '9px', borderRadius: '8px', border: `1px solid ${tpl.color}30`,
            background: `${tpl.color}15`, color: tpl.color,
            fontSize: '13px', fontWeight: 600, cursor: 'pointer',
            fontFamily: 'Inter, system-ui, sans-serif',
          }}
        >
          <Play size={12} fill="currentColor" />
          Lanzar con este template
        </button>
      </div>
    </motion.div>
  )
}

function MetaRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
      <span style={{ color: 'var(--muted)' }}>{label}</span>
      <span style={{ color: 'var(--text)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

const sectionLabel = {
  fontSize: '10px', fontWeight: 700, textTransform: 'uppercase',
  letterSpacing: '0.08em', color: 'var(--muted)', marginBottom: '8px',
}

export function TemplatesView({ onViewChange }) {
  const [cat, setCat] = useState('all')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)

  const filtered = TEMPLATES.filter(t => {
    if (cat !== 'all' && t.cat !== cat) return false
    if (search && !t.label.toLowerCase().includes(search.toLowerCase()) && !t.desc.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const handleLaunch = (tpl) => {
    // Navigate to missions and pre-fill with template mode
    if (onViewChange) onViewChange('missions')
  }

  return (
    <div className="view-shell">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div>
          <h1 className="view-title">Plantillas</h1>
          <p className="view-subtitle">{TEMPLATES.length} plantillas de misión disponibles.</p>
        </div>
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '2px', background: 'rgba(255,255,255,0.04)', padding: '3px', borderRadius: '8px', flexWrap: 'wrap' }}>
          {CATEGORIES.map(c => (
            <button key={c.id} onClick={() => setCat(c.id)} style={{
              padding: '4px 10px', borderRadius: '5px', border: 'none', cursor: 'pointer',
              fontSize: '12px', fontWeight: 500, fontFamily: 'Inter, system-ui, sans-serif',
              display: 'flex', alignItems: 'center', gap: '5px', transition: 'all 0.12s',
              background: cat === c.id ? 'rgba(136,117,255,0.2)' : 'transparent',
              color: cat === c.id ? '#a899ff' : 'var(--muted)',
            }}>
              {c.label}
              <span style={{ fontSize: '10px', fontWeight: 700, padding: '0 5px', borderRadius: '8px', background: cat === c.id ? 'rgba(136,117,255,0.3)' : 'rgba(255,255,255,0.08)' }}>
                {c.count}
              </span>
            </button>
          ))}
        </div>
        <div style={{ position: 'relative', marginLeft: 'auto' }}>
          <Search size={12} style={{ position: 'absolute', left: '9px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar template..." style={searchInput} />
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', background: 'rgba(255,255,255,0.01)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: '12px' }}>
            {filtered.map(tpl => (
              <TemplateCard
                key={tpl.id}
                tpl={tpl}
                onLaunch={handleLaunch}
                onSelect={setSelected}
                active={selected?.id === tpl.id}
              />
            ))}
          </div>
        </div>

        <AnimatePresence>
          {selected && (
            <TemplateDetail
              tpl={selected}
              onLaunch={handleLaunch}
              onClose={() => setSelected(null)}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// ── Shared styles ───────────────────────────────────────────────────
const searchInput = { paddingLeft: '28px', paddingRight: '10px', paddingTop: '6px', paddingBottom: '6px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '7px', color: 'var(--text)', fontSize: '12px', fontFamily: 'Inter, system-ui, sans-serif', outline: 'none', width: '180px' }
