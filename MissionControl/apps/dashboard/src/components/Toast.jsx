import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, CheckCircle2, AlertTriangle, Zap } from 'lucide-react'

const TOAST_DURATION = 5000
const MAX_TOASTS = 3

const ICONS = {
  success: <CheckCircle2 size={16} style={{ color: 'var(--success)' }} />,
  warning: <AlertTriangle size={16} style={{ color: 'var(--warning)' }} />,
  error: <AlertTriangle size={16} style={{ color: 'var(--danger)' }} />,
  info: <Zap size={16} style={{ color: 'var(--info)' }} />,
}

export function useToasts() {
  const [toasts, setToasts] = useState([])
  const idRef = useRef(0)

  const addToast = useCallback((title, message, type = 'info') => {
    const id = ++idRef.current
    setToasts(prev => [...prev.slice(-(MAX_TOASTS - 1)), { id, title, message, type }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, TOAST_DURATION)
  }, [])

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  return { toasts, addToast, dismiss }
}

export function useEventToasts(events, addToast) {
  const prevLen = useRef(events?.length ?? 0)

  useEffect(() => {
    if (!events || events.length <= prevLen.current) {
      prevLen.current = events?.length ?? 0
      return
    }
    const newEvents = events.slice(prevLen.current)
    prevLen.current = events.length

    for (const evt of newEvents.slice(-2)) {
      const type = evt.event_type
      if (type === 'mission_started' || type === 'mission_completed') {
        addToast(
          type === 'mission_started' ? 'Misi\u00f3n iniciada' : 'Misi\u00f3n completada',
          evt.summary || evt.actor || '',
          type === 'mission_completed' ? 'success' : 'info'
        )
      } else if (type === 'task_completed') {
        addToast('Tarea completada', evt.summary || '', 'success')
      } else if (type === 'agent_error') {
        addToast('Error de agente', evt.summary || '', 'error')
      }
    }
  }, [events, addToast])
}

export function ToastContainer({ toasts, onDismiss }) {
  return (
    <div className="toast-container">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div
            key={toast.id}
            className="toast"
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          >
            <div className="toast-icon">{ICONS[toast.type] || ICONS.info}</div>
            <div className="toast-content">
              <div className="toast-title">{toast.title}</div>
              {toast.message && <div className="toast-message">{toast.message}</div>}
            </div>
            <button className="toast-dismiss" onClick={() => onDismiss(toast.id)}>
              <X size={14} />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
