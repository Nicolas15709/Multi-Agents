import { motion } from 'framer-motion'
import { Clock, MessageSquare, TerminalSquare, RefreshCw, Box, Layers, Target, Database } from 'lucide-react'

const EVENT_ICONS = {
  system_log: TerminalSquare,
  mission_state: RefreshCw,
  agent_thought: MessageSquare,
  task_update: Box,
  default: Database,
}

function prettyEventType(value) {
  return (value || 'event').replaceAll('_', ' ')
}

function formatTime(value) {
  if (!value) return 'n/a'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString()
}

function payloadSummary(payload) {
  if (!payload || typeof payload !== 'object') return null
  const keys = Object.keys(payload).slice(0, 3)
  if (keys.length === 0) return null
  return Object.values(payload).map(v => typeof v === 'object' ? JSON.stringify(v).slice(0, 20) + '...' : String(v)).join(' | ')
}

export function TimelinePanel({ events = [] }) {
  return (
    <div style={{ padding: '0 8px' }}>
      {events.length === 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '150px', opacity: 0.5 }}>
          <Clock size={24} style={{ marginBottom: '8px' }} />
          <p className="muted" style={{ fontSize: '11px' }}>Sin eventos todavía.</p>
        </div>
      ) : (
        <div className="timeline-list">
          {events.map((event, index) => {
            const IconComponent = EVENT_ICONS[event.event_type] || EVENT_ICONS.default

            return (
              <motion.div 
                key={event.id} 
                className="timeline-item"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: 'rgba(99, 102, 241, 0.1)',
                  border: '1px solid rgba(99, 102, 241, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  marginTop: '2px',
                  boxShadow: '0 0 10px rgba(99, 102, 241, 0.1)'
                }}>
                  <IconComponent size={10} color="var(--accent-3)" />
                </div>
                
                <div className="timeline-content">
                  <div className="timeline-head">
                    <strong style={{ fontSize: '11.5px', color: 'var(--text-bright)' }}>{event.summary}</strong>
                    <span className="meta-chip">{formatTime(event.created_at)}</span>
                  </div>
                  <div className="muted" style={{ fontSize: '10px', marginTop: '2px' }}>
                    <span style={{ color: 'var(--accent-2)', fontWeight: 600 }}>{event.actor || 'system'}</span>
                    {' · '}
                    {prettyEventType(event.event_type)}
                  </div>
                  {event.payload && Object.keys(event.payload).length > 0 && (
                     <div className="timeline-payload">
                       {payloadSummary(event.payload)}
                     </div>
                  )}
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
