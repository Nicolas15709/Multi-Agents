import { useMemo, useState } from 'react'
import { Rocket, Terminal as TerminalIcon } from 'lucide-react'
import { motion } from 'framer-motion'
import { createMission } from '../runtimeApi'

const MODES = [
  'software_build',
  'prototype_to_build',
  'landing_launch',
  'feature_extension',
  'bugfix_debug',
  'documentation_pack',
  'research_only',
]

export function MissionLauncher() {
  const [title, setTitle] = useState('')
  const [goal, setGoal] = useState('')
  const [mode, setMode] = useState('feature_extension')
  const [priority, setPriority] = useState('medium')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const preview = useMemo(() => {
    if (!title && !goal) return null
    return `python3 submit_mission.py "${title || 'Mission title'}" "${goal || 'Mission goal'}" --mode ${mode} --priority ${priority}`
  }, [title, goal, mode, priority])

  async function handleSubmit(event) {
    event.preventDefault()
    if (!title.trim() || !goal.trim()) {
      setFeedback({ kind: 'error', text: 'Completa el título y el objetivo.' })
      return
    }

    try {
      setIsSubmitting(true)
      setFeedback(null)
      const result = await createMission({
        title: title.trim(),
        goal: goal.trim(),
        mode,
        priority,
        source: 'api',
        allow_24x7: true,
      })
      setFeedback({ kind: 'success', text: `Misión creada: ${result.mission_id}` })
      setTitle('')
      setGoal('')
    } catch (error) {
      setFeedback({ kind: 'error', text: error instanceof Error ? error.message : 'No se pudo crear la misión.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="panel panel-section" style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.05), transparent)' }}>
      <div className="stack-head">
        <h2 className="section-title">
          <Rocket size={12} /> Launch Protocol
        </h2>
        <span className="section-count">API + CLI</span>
      </div>

      <form className="launcher-form" onSubmit={handleSubmit}>
        <label className="field-label">
          <span>Mission Title</span>
          <input 
            value={title} 
            onChange={(event) => setTitle(event.target.value)} 
            placeholder="e.g. Implement Webhooks..." 
          />
        </label>

        <label className="field-label">
          <span>Objective Goal</span>
          <textarea 
            value={goal} 
            onChange={(event) => setGoal(event.target.value)} 
            rows={2} 
            placeholder="Define strict outcomes for the agency..." 
          />
        </label>

        <div className="launcher-grid">
          <label className="field-label">
            <span>Operating Mode</span>
            <select value={mode} onChange={(event) => setMode(event.target.value)}>
              {MODES.map((item) => <option key={item} value={item}>{item.replace(/_/g, ' ')}</option>)}
            </select>
          </label>

          <label className="field-label">
            <span>Priority</span>
            <select value={priority} onChange={(event) => setPriority(event.target.value)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '16px', flexWrap: 'wrap' }}>
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              borderRadius: '10px',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              background: 'rgba(16, 185, 129, 0.14)',
              color: '#8bf3d4',
              fontWeight: 700,
              cursor: isSubmitting ? 'wait' : 'pointer',
            }}
          >
            <Rocket size={14} />
            {isSubmitting ? 'Creando...' : 'Crear misión'}
          </button>
          {feedback && (
            <span style={{ fontSize: '12px', color: feedback.kind === 'success' ? 'var(--accent)' : 'var(--danger)' }}>
              {feedback.text}
            </span>
          )}
        </div>
      </form>

      <motion.div 
        className="launcher-output" 
        layout
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        style={{ marginTop: '16px', background: 'var(--bg)', borderColor: 'var(--panel-border-hover)' }}
      >
        <div className="stat-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <TerminalIcon size={10} color="var(--accent)" /> CLI Submission Command
        </div>
        <code style={{ fontSize: '10px', paddingTop: '8px', paddingBottom: '4px' }}>
          {preview || 'Complete parameters to generate cli input.'}
        </code>
      </motion.div>
    </section>
  )
}
