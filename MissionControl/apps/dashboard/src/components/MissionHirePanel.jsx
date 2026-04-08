import { useEffect, useMemo, useState } from 'react'
import { Briefcase, Check, Plus, Search, Sparkles, UserPlus } from 'lucide-react'
import { approveHireRequest, fetchAgentTemplates, fetchHireSuggestions, hireSubagent } from '../runtimeApi'

const EMPTY_FORM = {
  template_id: '',
  display_name: '',
  role: '',
  personality: '',
  capabilities: '',
  notes: '',
  budget_monthly_cents: '',
}

function renderDivisionPill(label, isActive, onClick) {
  return (
    <button
      key={label}
      type="button"
      onClick={onClick}
      style={{
        padding: '4px 9px',
        borderRadius: '999px',
        border: `1px solid ${isActive ? 'rgba(56, 189, 248, 0.28)' : 'rgba(255,255,255,0.08)'}`,
        background: isActive ? 'rgba(56, 189, 248, 0.13)' : 'rgba(255,255,255,0.03)',
        color: isActive ? '#97dfff' : 'var(--muted)',
        fontSize: '10px',
        fontWeight: 700,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  )
}

export function MissionHirePanel({ mission, hireRequests = [] }) {
  const [form, setForm] = useState(EMPTY_FORM)
  const [suggestions, setSuggestions] = useState([])
  const [catalog, setCatalog] = useState([])
  const [catalogQuery, setCatalogQuery] = useState('')
  const [catalogDivision, setCatalogDivision] = useState('all')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [activeRequestId, setActiveRequestId] = useState(null)
  const [localCreatedRequests, setLocalCreatedRequests] = useState([])
  const [localRequestPatches, setLocalRequestPatches] = useState({})
  const [refreshKey, setRefreshKey] = useState(0)
  const [feedback, setFeedback] = useState(null)

  const recentHires = useMemo(() => {
    const missionScoped = hireRequests
      .filter((item) => item.mission_id === mission?.id)
      .map((item) => ({ ...item, ...(localRequestPatches[item.id] || {}) }))
    const existingIds = new Set(missionScoped.map((item) => item.id))
    const pendingLocal = localCreatedRequests.filter((item) => item.mission_id === mission?.id && !existingIds.has(item.id))
    return [...pendingLocal, ...missionScoped].slice(0, 6)
  }, [hireRequests, localCreatedRequests, localRequestPatches, mission?.id])

  const selectedTemplate = useMemo(
    () => catalog.find((item) => item.id === form.template_id) || null,
    [catalog, form.template_id],
  )

  const divisionOptions = useMemo(() => {
    const divisions = Array.from(new Set(catalog.map((item) => item.division_label).filter(Boolean)))
    return ['all', ...divisions]
  }, [catalog])

  const visibleCatalog = useMemo(() => {
    const query = catalogQuery.trim().toLowerCase()
    return catalog
      .filter((item) => {
        if (catalogDivision !== 'all' && item.division_label !== catalogDivision) return false
        if (!query) return true
        return (
          item.display_name?.toLowerCase().includes(query)
          || item.description?.toLowerCase().includes(query)
          || item.role?.toLowerCase().includes(query)
          || item.division_label?.toLowerCase().includes(query)
        )
      })
      .slice(0, 10)
  }, [catalog, catalogDivision, catalogQuery])

  useEffect(() => {
    let cancelled = false
    async function loadCatalog() {
      try {
        const next = await fetchAgentTemplates({ limit: 180 })
        if (!cancelled) setCatalog(next)
      } catch (_error) {
        if (!cancelled) setCatalog([])
      }
    }
    loadCatalog()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadSuggestions() {
      if (!mission?.id) return
      try {
        const next = await fetchHireSuggestions(mission.id)
        if (!cancelled) setSuggestions(next)
      } catch (_error) {
        if (!cancelled) setSuggestions([])
      }
    }
    loadSuggestions()
    return () => {
      cancelled = true
    }
  }, [mission?.id, recentHires.length, refreshKey])

  function updateField(key, value) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  function applySuggestion(suggestion) {
    setForm({
      template_id: suggestion.template_id || suggestion.id || '',
      display_name: suggestion.display_name || '',
      role: suggestion.role || '',
      personality: suggestion.personality || '',
      capabilities: Array.isArray(suggestion.capabilities) ? suggestion.capabilities.join(', ') : '',
      notes: suggestion.notes || suggestion.description || '',
      budget_monthly_cents: '',
    })
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!mission?.id) return
    if (!form.display_name.trim() || !form.role.trim()) {
      setFeedback({ kind: 'error', text: 'Pon al menos nombre y rol del subagente.' })
      return
    }

    try {
      setIsSubmitting(true)
      setFeedback(null)
      const result = await hireSubagent(mission.id, {
        template_id: form.template_id || undefined,
        display_name: form.display_name.trim(),
        role: form.role.trim(),
        personality: form.personality.trim() || undefined,
        capabilities: form.capabilities,
        notes: form.notes.trim() || undefined,
        budget_monthly_cents: form.budget_monthly_cents ? Number(form.budget_monthly_cents) : 0,
      })
      const successText = result.status === 'pending'
        ? `Solicitud creada: ${form.display_name.trim()} queda pendiente de aprobación.`
        : result.duplicate
          ? 'Ya existe una solicitud activa o un hire con ese nombre y rol.'
          : `Subagente activado: ${result.agent_id}`
      setFeedback({ kind: 'success', text: successText })
      if (!result.duplicate && result.hire_request_id) {
        setLocalCreatedRequests((current) => [
          {
            id: result.hire_request_id,
            mission_id: mission.id,
            display_name: form.display_name.trim(),
            role: form.role.trim(),
            capabilities: form.capabilities
              .split(',')
              .map((item) => item.trim())
              .filter(Boolean),
            status: result.status || (result.agent_id ? 'hired' : 'pending'),
            hired_agent_id: result.agent_id || null,
            metadata: selectedTemplate ? {
              template_id: selectedTemplate.id,
              template_division: selectedTemplate.division,
              template_division_label: selectedTemplate.division_label,
            } : {},
          },
          ...current.filter((item) => item.id !== result.hire_request_id),
        ])
      }
      setForm(EMPTY_FORM)
      setRefreshKey((value) => value + 1)
    } catch (error) {
      setFeedback({ kind: 'error', text: error instanceof Error ? error.message : 'No se pudo contratar el subagente.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleApprove(hireRequestId) {
    try {
      setActiveRequestId(hireRequestId)
      setFeedback(null)
      const result = await approveHireRequest(hireRequestId)
      setFeedback({ kind: 'success', text: `Subagente aprobado: ${result.agent_id}` })
      setLocalRequestPatches((current) => ({
        ...current,
        [hireRequestId]: {
          status: 'hired',
          hired_agent_id: result.agent_id,
        },
      }))
      setRefreshKey((value) => value + 1)
    } catch (error) {
      setFeedback({ kind: 'error', text: error instanceof Error ? error.message : 'No se pudo aprobar el subagente.' })
    } finally {
      setActiveRequestId(null)
    }
  }

  if (!mission) return null

  return (
    <section className="panel panel-section" style={{ background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.06), transparent)' }}>
      <div className="stack-head">
        <h2 className="section-title">
          <UserPlus size={12} /> Contratar subagente
        </h2>
        <span className="section-count">Agency roster</span>
      </div>

      {suggestions.length > 0 && (
        <div style={{ display: 'grid', gap: '8px', marginBottom: '14px' }}>
          <div className="stat-label">Sugerencias automáticas del lead</div>
          <div style={{ display: 'grid', gap: '8px' }}>
            {suggestions.slice(0, 4).map((item) => (
              <button
                key={`${item.template_id || item.display_name}-${item.role}`}
                type="button"
                onClick={() => applySuggestion(item)}
                style={{
                  textAlign: 'left',
                  display: 'grid',
                  gap: '5px',
                  padding: '11px 12px',
                  borderRadius: '10px',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  color: 'inherit',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
                  <strong style={{ fontSize: '12px', color: 'var(--text-bright)' }}>
                    {item.emoji ? `${item.emoji} ` : ''}{item.display_name}
                  </strong>
                  {item.division_label && <span style={{ fontSize: '10px', color: 'var(--muted)' }}>{item.division_label}</span>}
                </div>
                <span style={{ fontSize: '10px', color: 'var(--muted)' }}>{item.description || item.notes}</span>
                <span style={{ fontSize: '10px', color: 'var(--muted)' }}>
                  {Array.isArray(item.capabilities) ? item.capabilities.slice(0, 4).join(', ') : ''}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gap: '8px', marginBottom: '14px' }}>
        <div className="stat-label">Plantillas listas para contratar</div>
        <div style={{ display: 'grid', gap: '8px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={12} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
            <input
              value={catalogQuery}
              onChange={(event) => setCatalogQuery(event.target.value)}
              placeholder="Buscar specialist, SEO, PM, marketing, ventas..."
              style={{ width: '100%', padding: '9px 10px 9px 30px' }}
            />
          </div>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {divisionOptions.map((label) => renderDivisionPill(label === 'all' ? 'All' : label, catalogDivision === label, () => setCatalogDivision(label)))}
          </div>
          <div style={{ display: 'grid', gap: '8px' }}>
            {visibleCatalog.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--muted)', border: '1px dashed rgba(255,255,255,0.08)', borderRadius: '10px', padding: '12px' }}>
                No hay plantillas que coincidan con ese filtro.
              </div>
            ) : (
              visibleCatalog.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => applySuggestion(item)}
                  style={{
                    textAlign: 'left',
                    display: 'grid',
                    gap: '5px',
                    padding: '11px 12px',
                    borderRadius: '10px',
                    background: selectedTemplate?.id === item.id ? 'rgba(56, 189, 248, 0.12)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${selectedTemplate?.id === item.id ? 'rgba(56, 189, 248, 0.28)' : 'rgba(255,255,255,0.06)'}`,
                    color: 'inherit',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center' }}>
                    <strong style={{ fontSize: '12px', color: 'var(--text-bright)' }}>
                      {item.emoji ? `${item.emoji} ` : ''}{item.display_name}
                    </strong>
                    <span style={{ fontSize: '10px', color: 'var(--muted)' }}>{item.division_label}</span>
                  </div>
                  <span style={{ fontSize: '10px', color: 'var(--muted)' }}>{item.description}</span>
                  <span style={{ fontSize: '10px', color: 'var(--muted)' }}>
                    {Array.isArray(item.capabilities) ? item.capabilities.slice(0, 4).join(', ') : ''}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: '10px' }}>
        {selectedTemplate && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '10px',
            padding: '10px 12px',
            borderRadius: '10px',
            border: '1px solid rgba(56, 189, 248, 0.22)',
            background: 'rgba(56, 189, 248, 0.08)',
          }}>
            <div style={{ display: 'grid', gap: '3px' }}>
              <strong style={{ fontSize: '12px', color: '#bfefff' }}>Template seleccionada: {selectedTemplate.display_name}</strong>
              <span style={{ fontSize: '10px', color: 'var(--muted)' }}>{selectedTemplate.division_label} · {selectedTemplate.role}</span>
            </div>
            <button type="button" onClick={() => setForm((current) => ({ ...current, template_id: '' }))} style={{ fontSize: '10px', padding: '6px 8px' }}>
              Limpiar
            </button>
          </div>
        )}

        <div className="launcher-grid">
          <label className="field-label">
            <span>Nombre</span>
            <input value={form.display_name} onChange={(event) => updateField('display_name', event.target.value)} placeholder="Ej. Social Media Strategist" />
          </label>
          <label className="field-label">
            <span>Rol</span>
            <input value={form.role} onChange={(event) => updateField('role', event.target.value)} placeholder="Ej. social-media-strategist" />
          </label>
        </div>

        <label className="field-label">
          <span>Personalidad / descripción</span>
          <textarea
            rows={3}
            value={form.personality}
            onChange={(event) => updateField('personality', event.target.value)}
            placeholder="Cómo trabaja, cómo decide y qué calidad esperas."
          />
        </label>

        <label className="field-label">
          <span>Capacidades</span>
          <input
            value={form.capabilities}
            onChange={(event) => updateField('capabilities', event.target.value)}
            placeholder="react, linkedin, seo, funnel, ga4, auth, tests"
          />
        </label>

        <div className="launcher-grid">
          <label className="field-label">
            <span>Budget mensual (opcional)</span>
            <input
              type="number"
              min="0"
              value={form.budget_monthly_cents}
              onChange={(event) => updateField('budget_monthly_cents', event.target.value)}
              placeholder="0"
            />
          </label>
          <label className="field-label">
            <span>Notas para la misión</span>
            <input
              value={form.notes}
              onChange={(event) => updateField('notes', event.target.value)}
              placeholder="Qué debe atacar exactamente"
            />
          </label>
        </div>

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
              border: '1px solid rgba(56, 189, 248, 0.28)',
              background: 'rgba(56, 189, 248, 0.14)',
              color: '#97dfff',
              fontWeight: 700,
              cursor: isSubmitting ? 'wait' : 'pointer',
            }}
          >
            <Plus size={14} />
            {isSubmitting ? 'Contratando...' : 'Contratar especialista'}
          </button>
          {feedback && (
            <span style={{ fontSize: '12px', color: feedback.kind === 'success' ? 'var(--accent)' : 'var(--danger)' }}>
              {feedback.text}
            </span>
          )}
        </div>
      </form>

      <div style={{ marginTop: '14px', display: 'grid', gap: '8px' }}>
        <div className="stat-label">Subagentes recientes</div>
        {recentHires.length === 0 ? (
          <div style={{ fontSize: '12px', color: 'var(--muted)', border: '1px dashed rgba(255,255,255,0.08)', borderRadius: '10px', padding: '12px' }}>
            Esta misión aún no tiene hires dinámicos.
          </div>
        ) : (
          recentHires.map((item) => (
            <div
              key={item.id}
              style={{
                display: 'grid',
                gap: '5px',
                padding: '12px',
                borderRadius: '10px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
                <strong style={{ fontSize: '12px', color: 'var(--text-bright)' }}>{item.display_name}</strong>
                <span style={{ fontSize: '10px', color: 'var(--muted)' }}>{item.status}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', fontSize: '10px', color: 'var(--muted)' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <Briefcase size={11} />
                  {item.role}
                </span>
                {item.metadata?.template_division_label && (
                  <span>{item.metadata.template_division_label}</span>
                )}
                {item.capabilities?.length > 0 && (
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Sparkles size={11} />
                    {item.capabilities.join(', ')}
                  </span>
                )}
              </div>
              {item.status === 'pending' && (
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={() => handleApprove(item.id)}
                    disabled={activeRequestId === item.id}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '7px 10px',
                      borderRadius: '8px',
                      border: '1px solid rgba(0, 212, 160, 0.25)',
                      background: 'rgba(0, 212, 160, 0.12)',
                      color: '#7ef2cf',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: activeRequestId === item.id ? 'wait' : 'pointer',
                    }}
                  >
                    <Check size={12} />
                    {activeRequestId === item.id ? 'Aprobando...' : 'Aprobar hire'}
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  )
}
