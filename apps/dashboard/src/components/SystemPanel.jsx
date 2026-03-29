import { motion, AnimatePresence } from 'framer-motion';

export function SystemPanel({ stream }) {
  const notifications = stream?.notifications || []
  return (
    <div className="panel-section">
      <h2 className="section-title">System Insights</h2>
      <div className="system-feed">
        <AnimatePresence mode="popLayout">
          {notifications.length === 0 ? (
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="muted"
            >
              Sin notificaciones recientes.
            </motion.p>
          ) : (
            notifications.map((item, i) => (
              <motion.div 
                key={item.id} 
                className="event-item"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.05 }}
              >
                {item.summary}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
