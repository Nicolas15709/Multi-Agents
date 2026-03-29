import { motion, AnimatePresence } from 'framer-motion';

export function TaskPanel({ tasks = [] }) {
  return (
    <div className="panel-section">
      <h2 className="section-title">Tasks</h2>
      <div className="task-list">
        <AnimatePresence mode="popLayout">
          {tasks.length === 0 ? (
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="muted"
            >
              No hay tareas todavía.
            </motion.p>
          ) : (
            tasks.map((task, i) => (
              <motion.div 
                key={task.id} 
                className="task-item"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <div className="task-head">
                  <strong>{task.title}</strong>
                  <span className="state-pill" data-status={task.status.toLowerCase()}>{task.status}</span>
                </div>
                <div className="muted">{task.agent_id} · prioridad {task.priority}</div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
