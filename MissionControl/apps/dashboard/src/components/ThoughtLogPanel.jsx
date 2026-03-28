export function ThoughtLogPanel({ events = [] }) {
  const thoughtEvents = events.filter((event) => event.event_type === 'thought_step')

  return (
    <section className="panel panel-section">
      <div className="stack-head">
        <h2 className="section-title">Thought log</h2>
        <span className="section-count">{thoughtEvents.length}</span>
      </div>

      {thoughtEvents.length === 0 ? (
        <p className="muted">Todavía no hay pasos de pensamiento registrados.</p>
      ) : (
        thoughtEvents.map((event) => (
          <div key={event.id} className="event-item">
            <div><strong>{event.summary}</strong></div>
            <div className="muted">{event.payload?.step || 'step'} · {event.payload?.detail ? JSON.stringify(event.payload.detail) : ''}</div>
          </div>
        ))
      )}
    </section>
  )
}
