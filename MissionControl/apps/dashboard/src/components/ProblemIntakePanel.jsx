import { useMemo, useState } from 'react'
import { AlertCircle, Send, Smartphone, CheckCircle2, Link2 } from 'lucide-react'
import { submitProblem } from '../runtimeApi'

const MODES = [
  { value: '', label: 'Auto-detectar' },
  { value: 'bugfix_debug', label: 'Bugfix / Debug' },
  { value: 'feature_extension', label: 'Feature Extension' },
  { value: 'security_review', label: 'Security Review' },
  { value: 'research_only', label: 'Research Only' },
  { value: 'documentation_pack', label: 'Documentation' },
]

const STATUS_LABELS = {
  pending: 'Pendiente',
  dispatched: 'Enviada al equipo',
  duplicate: 'Duplicada',
  resolved: 'Resuelta',
  rejected: 'Rechazada',
}

export function ProblemIntakePanel({ requests = [] }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('high')
  const [mode, setMode] = useState('')
  const [requestedBy, setRequestedBy] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const recentRequests = useMemo(() => requests.slice(0, 5), [requests])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!description.trim()) {
      setFeedback({ kind: 'error', text: 'Describe el problema para poder enviarlo.' })
      return
    }

    try {
      setIsSubmitting(true)
      setFeedback(null)
      const result = await submitProblem({
        title: title.trim() || undefined,
        description: description.trim(),
        priority,
        mode: mode || undefined,
        requested_by: requestedBy.trim() || undefined,
        channel: 'mobile',
        source: 'mobile',
        auto_dispatch: true,
      })
      if (result.duplicate) {
        setFeedback({
          kind: 'success',
          text: `Ya existía una solicitud activa${result.mission_id ? ` → misión ${result.mission_id}` : ''}.`,
        })
      } else {
        setFeedback({
          kind: 'success',
          text: `Solicitud enviada${result.mission_id ? ` → misión ${result.mission_id}` : ''}.`,
        })
      }
      setTitle('')
      setDescription('')
      setRequestedBy('')
      setMode('')
      setPriority('high')
    } catch (error) {
      setFeedback({ kind: 'error', text: error instanceof Error ? error.message : 'No se pudo enviar el problema.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="panel panel-section" style={{ background: 'linear-gradient(135deg, rgba(255, 169, 64, 0.06), transparent)' }}>
      <div className="stack-head">
        <h2 className="section-title">
          <Smartphone size={12} /> Entrada móvil
        </h2>
        <span className="section-count">OpenClaw-ready</span>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '12px' }}>
        <label className="field-label">
          <span>Título corto</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Login roto en móvil"
          />
        </label>

        <label className="field-label">
          <span>Problema / pedido</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            placeholder="Describe el problema o la tarea como se la mandarías a OpenClaw..."
          />
        </label>

        <div className="launcher-grid">
          <label className="field-label">
            <span>Prioridad</span>
            <select value={priority} onChange={(event) => setPriority(event.target.value)}>
              <option value="medium">Media</option>
              <option value="high">Alta</option>
              <option value="critical">Crítica</option>
              <option value="low">Baja</option>
            </select>
          </label>

          <label className="field-label">
            <span>Modo</span>
            <select value={mode} onChange={(event) => setMode(event.target.value)}>
              {MODES.map((item) => (
                <option key={item.value || 'auto'} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="field-label">
          <span>Quién la reporta</span>
          <input
            value={requestedBy}
            onChange={(event) => setRequestedBy(event.target.value)}
            placeholder="Usuario / Cliente / Sistema"
          />
        </label>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              borderRadius: '10px',
              border: '1px solid rgba(255, 169, 64, 0.25)',
              background: 'rgba(255, 169, 64, 0.14)',
              color: '#ffd18f',
              fontWeight: 700,
              cursor: isSubmitting ? 'wait' : 'pointer',
            }}
          >
            <Send size={14} />
            {isSubmitting ? 'Enviando...' : 'Enviar problema'}
          </button>
          {feedback && (
            <span style={{ fontSize: '12px', color: feedback.kind === 'success' ? 'var(--accent)' : 'var(--danger)' }}>
              {feedback.text}
            </span>
          )}
        </div>
      </form>

      <div style={{ marginTop: '16px', display: 'grid', gap: '8px' }}>
        <div className="stat-label">Solicitudes recientes</div>
        {recentRequests.length === 0 ? (
          <div style={{ fontSize: '12px', color: 'var(--muted)', border: '1px dashed rgba(255,255,255,0.08)', borderRadius: '10px', padding: '12px' }}>
            Todavía no hay solicitudes en el inbox.
          </div>
        ) : (
          recentRequests.map((request) => (
            <div
              key={request.id}
              style={{
                display: 'grid',
                gap: '6px',
                padding: '12px',
                borderRadius: '10px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'space-between', flexWrap: 'wrap' }}>
                <strong style={{ fontSize: '12px', color: 'var(--text-bright)' }}>{request.title}</strong>
                <span style={{ fontSize: '10px', color: 'var(--muted)' }}>{STATUS_LABELS[request.status] || request.status}</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{request.description}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', fontSize: '10px', color: 'var(--muted)' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <AlertCircle size={11} />
                  {request.priority}
                </span>
                {request.mission_id && (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Link2 size={11} />
                    {request.mission_id}
                  </span>
                )}
                {request.status === 'dispatched' && (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: 'var(--accent)' }}>
                    <CheckCircle2 size={11} />
                    en ejecución
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
