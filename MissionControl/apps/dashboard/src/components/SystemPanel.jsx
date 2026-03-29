import { motion, AnimatePresence } from 'framer-motion'
import { Server, Bell, Activity } from 'lucide-react'

export function SystemPanel({ stream, progress }) {
  const notifications = stream?.notifications || []

  return (
    <section className="panel-section" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <div className="stack-head">
        <h2 className="section-title">
          <Server size={12} /> System Status
        </h2>
        {progress?.percent !== undefined && (
          <span className="section-count">{progress.percent}%</span>
        )}
      </div>

      {progress?.mission && (
        <div className="event-item" style={{ borderLeft: '2px solid var(--accent)', paddingLeft: '10px' }}>
          <div style={{ fontSize: '11px', fontWeight: 600 }}>{progress.mission.title}</div>
          <div className="muted" style={{ fontSize: '9px', marginTop: '2px' }}>
            {progress.progress?.done || 0}/{progress.progress?.total || 0} tasks · running {progress.progress?.running || 0}
          </div>
        </div>
      )}
      
      <div className="scroll-area" style={{ maxHeight: '180px' }}>
        {notifications.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60px', opacity: 0.5 }}>
            <Bell size={16} style={{ marginBottom: '4px' }} />
            <p className="muted" style={{ fontSize: '10px' }}>No notifications</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <AnimatePresence initial={false}>
              {notifications.map((item) => (
                <motion.div 
                  key={item.id} 
                  className="event-item"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                >
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <Activity size={10} color="var(--accent-2)" style={{ marginTop: '3px', flexShrink: 0 }} />
                    <span style={{ fontSize: '10px', lineHeight: 1.4 }}>{item.summary}</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </section>
  )
}
