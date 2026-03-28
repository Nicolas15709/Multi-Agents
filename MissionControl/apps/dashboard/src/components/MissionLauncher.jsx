import { useMemo, useState } from 'react'

const MODES = [
  'software_build',
  'prototype_to_build',
  'landing_launch',
  'feature_extension',
  'bugfix_debug',
  'documentation_pack',
  'security_review',
  'qa_hardening',
  'post_build_audit',
  'marketing_campaign',
  'brand_growth',
  'content_engine',
  'social_presence_audit',
  'business_audit_proposal',
  'competitor_intelligence',
  'offer_design',
  'research_only',
  'monitor_and_report',
  'launch_mode',
  'maintenance_cycle',
]

export function MissionLauncher() {
  const [title, setTitle] = useState('')
  const [goal, setGoal] = useState('')
  const [mode, setMode] = useState('feature_extension')
  const [priority, setPriority] = useState('medium')

  const preview = useMemo(() => {
    if (!title && !goal) return null
    return `python3 submit_mission.py "${title || 'Mission title'}" "${goal || 'Mission goal'}" --mode ${mode} --priority ${priority}`
  }, [title, goal, mode, priority])

  return (
    <section className="panel panel-section">
      <div className="stack-head">
        <h2 className="section-title">Mission launcher</h2>
        <span className="section-count">CLI-ready</span>
      </div>

      <div className="launcher-form">
        <label className="field-label">
          <span>Title</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ej. Improve dashboard live state" />
        </label>

        <label className="field-label">
          <span>Goal</span>
          <textarea value={goal} onChange={(event) => setGoal(event.target.value)} rows={3} placeholder="Qué debe lograr la misión" />
        </label>

        <div className="launcher-grid">
          <label className="field-label">
            <span>Mode</span>
            <select value={mode} onChange={(event) => setMode(event.target.value)}>
              {MODES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>

          <label className="field-label">
            <span>Priority</span>
            <select value={priority} onChange={(event) => setPriority(event.target.value)}>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
        </div>
      </div>

      <div className="launcher-output">
        <div className="stat-label">Submission preview</div>
        <code>{preview || 'Completa el formulario para generar el comando de misión.'}</code>
        <p className="muted">Siguiente fase: ejecutar este launcher directamente desde el dashboard con backend/auth real.</p>
      </div>
    </section>
  )
}
