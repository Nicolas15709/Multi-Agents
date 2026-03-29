import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, CircleDashed, Clock, AlertCircle, ListTodo } from 'lucide-react'

const staggerContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
}

const staggerItem = {
  hidden: { opacity: 0, x: -10 },
  show: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
}

const getStatusIcon = (status) => {
  switch(status?.toLowerCase()) {
    case 'done':
    case 'completed': return <CheckCircle2 size={14} color="var(--success)" />
    case 'running':
    case 'in_progress': return <CircleDashed size={14} color="var(--accent)" className="animate-spin" />
    case 'blocked':
    case 'failed': return <AlertCircle size={14} color="var(--danger)" />
    default: return <Clock size={14} color="var(--muted)" />
  }
}

export function TaskPanel({ tasks = [] }) {
  return (
    <section className="panel-section" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <div className="stack-head">
        <h2 className="section-title">
          <ListTodo size={12} /> Active Tasks
        </h2>
        <span className="section-count">{tasks.length}</span>
      </div>
<<<<<<< HEAD
      
      <div className="scroll-area" style={{ flex: 1 }}>
        {tasks.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100px', opacity: 0.5 }}>
            <ListTodo size={24} style={{ marginBottom: '8px' }} />
            <p className="muted" style={{ fontSize: '11px' }}>No hay tareas activas.</p>
=======
      {tasks.length === 0 ? (
        <p className="muted">No hay tareas todavía.</p>
      ) : (
        tasks.map((task) => (
          <div key={task.id} className="task-item">
            <div className="task-head">
              <strong>{task.title}</strong>
              <span className="state-pill">{task.status}</span>
            </div>
            <div className="muted">{task.agent_id} · prioridad {task.priority}{task.depends_on?.length ? ` · depende de ${task.depends_on.length}` : ''}</div>
>>>>>>> d05530c8abb00f53582858def9c6ff2f811a81aa
          </div>
        ) : (
          <motion.div variants={staggerContainer} initial="hidden" animate="show" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <AnimatePresence>
              {tasks.map((task) => (
                <motion.div key={task.id} variants={staggerItem} layout className="task-item">
                  <div className="task-head">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {getStatusIcon(task.status)}
                      <strong>{task.title}</strong>
                    </div>
                    <span className="state-pill" style={{
                      background: task.status === 'running' ? 'rgba(16, 185, 129, 0.1)' : '',
                      color: task.status === 'running' ? 'var(--accent)' : ''
                    }}>
                      {task.status}
                    </span>
                  </div>
                  <div className="muted" style={{ fontSize: '10px', marginTop: '6px', marginLeft: '22px' }}>
                    Agent: <span style={{ color: 'var(--text)', fontWeight: 600 }}>{task.agent_id}</span> · Priority: {task.priority}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </section>
  )
}
