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
  return keys.map((key) => `${key}: ${Array.isArray(payload[key]) ? payload[key].length + ' items' : String(payload[key])}`).join(' · ')
}

export function TimelinePanel({ events = [] }) {
  return (
    <section className="panel panel-section">
      <div className="stack-head">
        <h2 className="section-title">Mission timeline</h2>
        <span className="section-count">{events.length}</span>
      </div>

      {events.length === 0 ? (
        <p className="muted">Sin eventos todavía.</p>
      ) : (
        <div className="timeline-list">
          {events.map((event) => (
            <div key={event.id} className="timeline-item">
              <div className="timeline-dot" />
              <div className="timeline-content">
                <div className="timeline-head">
                  <strong>{event.summary}</strong>
                  <span className="meta-chip">{formatTime(event.created_at)}</span>
                </div>
                <div className="muted">{prettyEventType(event.event_type)} · {event.actor || 'system'}</div>
                {payloadSummary(event.payload) ? (
                  <div className="timeline-payload">{payloadSummary(event.payload)}</div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
