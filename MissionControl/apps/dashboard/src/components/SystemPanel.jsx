<<<<<<< HEAD
import { motion } from 'framer-motion'
import { Server, Bell } from 'lucide-react'

export function SystemPanel({ stream }) {
=======
export function SystemPanel({ stream, progress }) {
>>>>>>> d05530c8abb00f53582858def9c6ff2f811a81aa
  const notifications = stream?.notifications || []

  return (
<<<<<<< HEAD
    <section className="panel-section" style={{ display: 'flex', flexDirection: 'column', maxHeight: '200px' }}>
      <div className="stack-head">
        <h2 className="section-title">
          <Server size={12} /> System Alerts
        </h2>
        <span className="section-count">{notifications.length}</span>
      </div>
      
      <div className="scroll-area" style={{ flex: 1 }}>
        {notifications.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100px', opacity: 0.5 }}>
            <Bell size={20} style={{ marginBottom: '8px' }} />
            <p className="muted" style={{ fontSize: '11px' }}>Sin notificaciones recientes.</p>
          </div>
        ) : (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {notifications.map((item) => (
              <motion.div 
                key={item.id} 
                className="event-item"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                  <Bell size={12} color="var(--warning)" style={{ marginTop: '2px', flexShrink: 0 }} />
                  <span style={{ fontSize: '11px', lineHeight: 1.4 }}>{item.summary}</span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </section>
=======
    <div className="panel-section">
      <div className="stack-head">
        <h2 className="section-title">System</h2>
        <span className="section-count">{progress?.percent ?? 0}%</span>
      </div>
      {progress?.mission ? (
        <div className="event-item">
          <strong>{progress.mission.title}</strong>
          <div className="muted">{progress.progress?.done || 0}/{progress.progress?.total || 0} tareas · running {progress.progress?.running || 0} · blocked {progress.progress?.blocked || 0}</div>
        </div>
      ) : null}
      {notifications.length === 0 ? (
        <p className="muted">Sin notificaciones recientes.</p>
      ) : (
        notifications.map((item) => (
          <div key={item.id} className="event-item">{item.summary}</div>
        ))
      )}
    </div>
>>>>>>> d05530c8abb00f53582858def9c6ff2f811a81aa
  )
}
