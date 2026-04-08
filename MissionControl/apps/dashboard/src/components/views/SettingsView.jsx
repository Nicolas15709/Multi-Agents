import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Settings, Bell, Shield, Globe, Key, Moon, Sun, Monitor,
  Cpu, MessageCircle, GitBranch, Database,
  ChevronRight, ToggleLeft, ToggleRight, Check, Info,
} from 'lucide-react'

function SettingRow({ icon: Icon, iconColor = '#8875ff', title, description, control, border = true }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '12px', padding: '14px 0',
      borderBottom: border ? '1px solid rgba(255,255,255,0.05)' : 'none',
    }}>
      <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: `${iconColor}12`, border: `1px solid ${iconColor}20`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <Icon size={14} style={{ color: iconColor }} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-bright)' }}>{title}</div>
        {description && <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '2px', lineHeight: 1.4 }}>{description}</div>}
      </div>
      {control}
    </div>
  )
}

function Toggle({ value, onChange }) {
  return (
    <button
      onClick={() => onChange(!value)}
      style={{
        width: '36px', height: '20px', borderRadius: '10px', border: 'none', cursor: 'pointer', flexShrink: 0,
        background: value ? '#8875ff' : 'rgba(255,255,255,0.12)', position: 'relative', transition: 'background 0.2s',
        padding: 0,
      }}
    >
      <div style={{
        width: '14px', height: '14px', borderRadius: '50%', background: '#fff',
        position: 'absolute', top: '3px', left: value ? '19px' : '3px', transition: 'left 0.2s',
      }} />
    </button>
  )
}

function SelectControl({ value, options, onChange }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{
        background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: '6px', color: 'var(--text)', fontSize: '12px', padding: '5px 8px',
        fontFamily: 'Inter, system-ui, sans-serif', cursor: 'pointer', outline: 'none',
      }}
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

function SectionCard({ title, children }) {
  return (
    <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '0 16px', marginBottom: '12px' }}>
      <div style={{ padding: '14px 0 10px', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '12px', fontWeight: 700, color: 'var(--text-bright)' }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function EnvVarHint({ varName }) {
  return (
    <code style={{ fontSize: '10px', background: 'rgba(136,117,255,0.1)', color: '#a899ff', padding: '1px 5px', borderRadius: '3px', border: '1px solid rgba(136,117,255,0.15)' }}>
      {varName}
    </code>
  )
}

export function SettingsView() {
  // UI preferences
  const [notifSound, setNotifSound] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [compactMode, setCompactMode] = useState(false)
  const [tickInterval, setTickInterval] = useState('5')
  const [snapshotPoll, setSnapshotPoll] = useState('10')
  const [logLevel, setLogLevel] = useState('info')

  // Notification prefs
  const [notifMissionDone, setNotifMissionDone] = useState(true)
  const [notifAgentBlocked, setNotifAgentBlocked] = useState(true)
  const [notifHeartbeat, setNotifHeartbeat] = useState(false)
  const [notifErrors, setNotifErrors] = useState(true)

  return (
    <div className="view-shell">
      {/* Header */}
      <div>
        <h1 className="view-title">Configuración</h1>
        <p className="view-subtitle">Preferencias del dashboard y ajustes del sistema.</p>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
        {/* General */}
        <SectionCard title="General">
          <SettingRow
            icon={Monitor}
            title="Modo compacto"
            description="Reduce el espacio entre elementos para ver más contenido."
            control={<Toggle value={compactMode} onChange={setCompactMode} />}
          />
          <SettingRow
            icon={Bell}
            title="Sonido de notificaciones"
            description="Reproduce un tono al recibir alertas del sistema."
            control={<Toggle value={notifSound} onChange={setNotifSound} />}
          />
          <SettingRow
            icon={ChevronRight}
            title="Auto-scroll en Timeline"
            description="Desplaza automáticamente al último evento registrado."
            control={<Toggle value={autoScroll} onChange={setAutoScroll} />}
            border={false}
          />
        </SectionCard>

        {/* Runtime */}
        <SectionCard title="Runtime">
          <SettingRow
            icon={Cpu}
            title="Intervalo de tick"
            description="Frecuencia de ejecución del orquestador Python (segundos)."
            control={<SelectControl value={tickInterval} onChange={setTickInterval} options={[
              { value: '5', label: '5s' }, { value: '10', label: '10s' },
              { value: '15', label: '15s' }, { value: '30', label: '30s' },
            ]} />}
          />
          <SettingRow
            icon={Database}
            title="Polling de snapshot"
            description="Frecuencia de actualización del dashboard (segundos)."
            control={<SelectControl value={snapshotPoll} onChange={setSnapshotPoll} options={[
              { value: '5', label: '5s' }, { value: '10', label: '10s' }, { value: '30', label: '30s' },
            ]} />}
          />
          <SettingRow
            icon={Settings}
            title="Nivel de log"
            description="Detalle de los mensajes en el log del sistema."
            control={<SelectControl value={logLevel} onChange={setLogLevel} options={[
              { value: 'debug', label: 'debug' }, { value: 'info', label: 'info' },
              { value: 'warn', label: 'warn' }, { value: 'error', label: 'error' },
            ]} />}
            border={false}
          />
        </SectionCard>

        {/* Notifications */}
        <SectionCard title="Notificaciones">
          <SettingRow
            icon={Check}
            iconColor="#00d4a0"
            title="Misión completada"
            description="Notificar cuando una misión finaliza exitosamente."
            control={<Toggle value={notifMissionDone} onChange={setNotifMissionDone} />}
          />
          <SettingRow
            icon={Bell}
            iconColor="#ffa940"
            title="Agente bloqueado"
            description="Alertar cuando un agente entra en estado de bloqueo."
            control={<Toggle value={notifAgentBlocked} onChange={setNotifAgentBlocked} />}
          />
          <SettingRow
            icon={Settings}
            iconColor="#ff4d6d"
            title="Errores del sistema"
            description="Notificar errores y fallos críticos del runtime."
            control={<Toggle value={notifErrors} onChange={setNotifErrors} />}
          />
          <SettingRow
            icon={Cpu}
            iconColor="rgba(255,255,255,0.3)"
            title="Heartbeat"
            description="Notificar cada latido del sistema (puede generar mucho ruido)."
            control={<Toggle value={notifHeartbeat} onChange={setNotifHeartbeat} />}
            border={false}
          />
        </SectionCard>

        {/* Integrations config (env vars reference) */}
        <SectionCard title="Variables de entorno">
          <div style={{ padding: '10px 0 6px', fontSize: '11px', color: 'var(--muted)', lineHeight: 1.6 }}>
            Configura estas variables en <code style={{ background: 'rgba(255,255,255,0.06)', padding: '1px 4px', borderRadius: '3px' }}>.env.vps</code> o en el entorno del VPS.
          </div>

          {[
            { label: 'Supabase URL',     var: 'SUPABASE_URL',              desc: 'URL del proyecto Supabase' },
            { label: 'Supabase Key',     var: 'SUPABASE_ANON_KEY',         desc: 'Clave anónima pública' },
            { label: 'OpenRouter Key',   var: 'OPENROUTER_API_KEY',         desc: 'API key para LLMs' },
            { label: 'Telegram Token',   var: 'TELEGRAM_BOT_TOKEN',         desc: 'Token del bot de Telegram' },
            { label: 'Telegram Chat ID', var: 'TELEGRAM_CHAT_ID',           desc: 'ID del chat de notificaciones' },
            { label: 'Slack Webhook',    var: 'SLACK_WEBHOOK_URL',          desc: 'Webhook URL de Slack' },
            { label: 'JWT Secret',       var: 'JWT_SECRET',                 desc: 'Secreto para tokens internos' },
            { label: 'WebSocket',        var: 'MISSION_CONTROL_WEBSOCKET',  desc: 'Habilitar WebSocket (true/false)' },
          ].map((item, i, arr) => (
            <div key={item.var} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 0', borderBottom: i < arr.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text)', marginBottom: '2px' }}>{item.label}</div>
                <div style={{ fontSize: '10px', color: 'var(--muted)' }}>{item.desc}</div>
              </div>
              <EnvVarHint varName={item.var} />
            </div>
          ))}
        </SectionCard>

        {/* Security */}
        <SectionCard title="Seguridad">
          <SettingRow
            icon={Shield}
            iconColor="#00d4a0"
            title="Row Level Security"
            description="RLS habilitado en Supabase por defecto. Revisar policies.sql."
            control={<span style={{ fontSize: '10px', color: '#00d4a0', fontWeight: 600 }}>Activo</span>}
          />
          <SettingRow
            icon={Key}
            iconColor="#ffa940"
            title="Secretos en entorno"
            description="Los secretos nunca se exponen al frontend. Siempre via .env."
            control={<span style={{ fontSize: '10px', color: '#00d4a0', fontWeight: 600 }}>Enforced</span>}
          />
          <SettingRow
            icon={Globe}
            iconColor="#8875ff"
            title="Login primero"
            description="Supabase Auth con Magic Link. Sin acceso sin autenticación."
            control={<span style={{ fontSize: '10px', color: '#00d4a0', fontWeight: 600 }}>Activo</span>}
            border={false}
          />
        </SectionCard>
      </div>
    </div>
  )
}

// ── Shared styles ───────────────────────────────────────────────────
