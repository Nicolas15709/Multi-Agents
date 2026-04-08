import { useRef, useEffect, useCallback, useState, useMemo } from 'react'
import { OfficeState } from './pixel-engine/engine/officeState'
import { startGameLoop } from './pixel-engine/engine/gameLoop'
import { computeContentBounds, renderFrame } from './pixel-engine/engine/renderer'
import { loadAllAssets } from './pixel-engine/browserAssetLoader'

const TILE_SIZE = 16
const FIT_PADDING_RATIO = 1
const MIN_ZOOM = 0.5
const EMPTY_AGENTS = []

export function PixelOffice({ agents = EMPTY_AGENTS, officeName = '' }) {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const officeStateRef = useRef(null)
  const zoomRef = useRef(1)
  const stopLoopRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const agentMapRef = useRef(new Map())

  // --- Pet Management State ---
  const [petsConfig, setPetsConfig] = useState(() => {
    try {
      const saved = localStorage.getItem('pixel-office-pets')
      return saved ? JSON.parse(saved) : []
    } catch (e) {
      return []
    }
  })

  // Persist pets to localStorage
  useEffect(() => {
    localStorage.setItem('pixel-office-pets', JSON.stringify(petsConfig))
  }, [petsConfig])

  // Sync pets with engine when config or engine state changes
  useEffect(() => {
    if (loading) return
    const os = officeStateRef.current
    if (os && os.syncPets) {
      os.syncPets(petsConfig)
    }
  }, [petsConfig, loading])

  const [isPetMenuOpen, setIsPetMenuOpen] = useState(false)
  const [petNameInput, setPetNameInput] = useState('Nuevo Amigo')

  // --- Pet Management Methods ---
  const addPet = useCallback((type) => {
    if (!petNameInput.trim()) return
    const id = `pet-${Date.now()}`
    setPetsConfig(prev => [...prev, { id, name: petNameInput, type }])
    setPetNameInput('Nuevo Amigo') // Reset for next pet
  }, [petNameInput])

  const removePet = useCallback((id) => {
    setPetsConfig(prev => prev.filter(p => p.id !== id))
  }, [])

  const calcFitZoom = useCallback(() => {
    const canvas = canvasRef.current
    const os = officeStateRef.current
    if (!canvas || !os) return 1

    const layout = os.getLayout()
    const bounds = computeContentBounds(
      os.tileMap,
      os.furniture,
      layout.tileColors,
      layout.cols,
      layout.rows,
    )
    const contentWidth = bounds.width || layout.cols * TILE_SIZE
    const contentHeight = bounds.height || layout.rows * TILE_SIZE
    const exact = Math.min(canvas.width / contentWidth, canvas.height / contentHeight)
    const padded = exact * FIT_PADDING_RATIO
    // Use 1/8th-step snapping (finer than 1/4th) to minimize margin loss from rounding
    return Math.max(MIN_ZOOM, Math.floor(padded * 8) / 8)
  }, [])

  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const rect = container.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1
    const width = Math.round(rect.width * dpr)
    const height = Math.round(rect.height * dpr)

    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width
      canvas.height = height
      const fit = calcFitZoom()
      if (fit > 0) {
        zoomRef.current = fit
      }
    }
  }, [calcFitZoom])

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    async function loadAssets() {
      const { layout } = await loadAllAssets('/pixel-assets')
      if (cancelled) return

      // Patch sign text with custom office name
      if (layout && officeName) {
        const sign = layout.furniture?.find(f => f.uid === 'sign-office')
        if (sign?.textConfig) {
          sign.textConfig.text = officeName.toUpperCase()
        }
      }

      const officeState = new OfficeState(layout || undefined)
      officeStateRef.current = officeState
      setLoading(false)
    }

    loadAssets().catch((err) => {
      console.error('[PixelOffice] Failed to load assets:', err)
      if (!cancelled) setLoading(false)
    })

    return () => {
      cancelled = true
      if (stopLoopRef.current) {
        stopLoopRef.current()
        stopLoopRef.current = null
      }
    }
  }, [officeName])

  useEffect(() => {
    if (loading) return
    const officeState = officeStateRef.current
    if (!officeState) return

    resizeCanvas()
    zoomRef.current = calcFitZoom()

    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.imageSmoothingEnabled = false

    const stop = startGameLoop(canvas, {
      update: (dt) => officeState.update(dt),
      render: (ctx2d) => {
        const zoom = zoomRef.current
        const canvasWidth = canvas.width
        const canvasHeight = canvas.height
        const layout = officeState.getLayout()
        const charsArray = Array.from(officeState.characters.values())

        renderFrame(
          ctx2d,
          canvasWidth,
          canvasHeight,
          officeState.tileMap,
          officeState.furniture,
          charsArray,
          zoom,
          0,
          0,
          undefined,
          undefined,
          layout.tileColors,
          layout.cols,
          layout.rows,
          officeState.pets || [],
        )
      },
    })
    stopLoopRef.current = stop

    return () => {
      if (stopLoopRef.current) {
        stopLoopRef.current()
        stopLoopRef.current = null
      }
    }
  }, [loading, resizeCanvas, calcFitZoom])

  useEffect(() => {
    const onResize = () => resizeCanvas()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [resizeCanvas])

  useEffect(() => {
    const os = officeStateRef.current
    if (!os) return

    const currentIds = new Set()

    agents.forEach((agent, index) => {
      const id = index
      currentIds.add(id)

      if (!os.characters.has(id)) {
        os.addAgent(
          id,
          agent.pixel_palette,
          agent.pixel_hue_shift,
          undefined,
          false,
          agent.display_name || agent.name || '',
        )
        agentMapRef.current.set(id, agent.agent_id)
      }

      const ch = os.characters.get(id)
      if (ch) {
        const isActive = agent.state !== 'idle'
        if (ch.isActive !== isActive) {
          os.setAgentActive(id, isActive)
        }
        if (isActive) {
          const tool = ['planning', 'researching'].includes(agent.state) ? 'Read' : 'Write'
          if (ch.currentTool !== tool) {
            os.setAgentTool(id, tool)
          }
        } else if (ch.currentTool) {
          os.setAgentTool(id, null)
        }
        const name = agent.display_name || agent.name || ''
        if (ch.name !== name) {
          ch.name = name
        }
      }
    })

    for (const [id] of os.characters) {
      if (id >= 0 && !currentIds.has(id)) {
        os.removeAgent(id)
        agentMapRef.current.delete(id)
      }
    }
  }, [agents])

  return (
    <section className="pixel-office-shell">
      <div ref={containerRef} className="pixel-office-canvas-wrap">
        {loading ? (
          <div className="pixel-office-loader">
            Cargando oficina virtual...
          </div>
        ) : (
          <>
            <canvas ref={canvasRef} className="pixel-office-canvas" />

            {/* Floating Toggle Button */}
            <button 
              className={`pet-toggle-fab ${isPetMenuOpen ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation()
                setIsPetMenuOpen((open) => !open)
              }}
              title="Gestionar Mascotas"
              type="button"
              aria-expanded={isPetMenuOpen}
              aria-controls="pet-management-sidebar"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 5c.67 0 1.35.09 2 .26 1.78-2 2.61-2.84 3.94-2.85C20 2.4 22 4 22 8c0 3.33-1 6-3 9-1.07 1.6-2.2 2.4-3.48 2.87-1.12.35-2.25.13-3.02-.37-.77.5-1.9.72-3.02.37-1.28-.47-2.41-1.27-3.48-2.87-2-3-3-5.67-3-9 0-4 2-5.6 4.06-5.59 1.33.01 2.16.85 3.94 2.85.65-.17 1.33-.26 2-.26Z" />
              </svg>
              {petsConfig.length > 0 && <span className="fab-badge">{petsConfig.length}</span>}
            </button>

            {/* Collapsible Pet Management Panel */}
            {isPetMenuOpen && (
            <div id="pet-management-sidebar" className="pet-management-sidebar open">
              <div className="pet-sidebar-header">
                <h3>Mascotas</h3>
                <button className="close-sidebar-inner" type="button" onClick={() => setIsPetMenuOpen(false)}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="pet-sidebar-content">
                <div className="pet-naming-section">
                  <label>Nombre de la mascota:</label>
                  <input 
                    type="text" 
                    className="pet-name-input"
                    value={petNameInput}
                    onChange={(e) => setPetNameInput(e.target.value)}
                    placeholder="Ponle un nombre..."
                  />
                </div>

                <div className="pet-add-grid-modern">
                  <button 
                    disabled={!petNameInput.trim()} 
                    className="pet-add-btn-v2 cat" 
                    type="button"
                    onClick={() => addPet('cat')}
                  >
                    <span className="icon">🐱</span>
                    <span>Añadir Gato</span>
                  </button>
                  <button 
                    disabled={!petNameInput.trim()} 
                    className="pet-add-btn-v2 dog" 
                    type="button"
                    onClick={() => addPet('dog')}
                  >
                    <span className="icon">🐶</span>
                    <span>Añadir Perro</span>
                  </button>
                </div>

                <div className="pet-inventory">
                  <div className="inventory-label">En la oficina:</div>
                  <div className="pet-scroller">
                    {petsConfig.length === 0 ? (
                      <div className="empty-inventory-msg">No hay mascotas acompañando hoy</div>
                    ) : (
                      petsConfig.map(pet => (
                        <div key={pet.id} className="pet-inventory-item">
                          <div className="pet-inventory-info">
                            <span className="type-dot" style={{ backgroundColor: pet.type === 'cat' ? 'var(--accent-2)' : 'var(--accent)' }}></span>
                            <span className="pet-name-display">{pet.name}</span>
                          </div>
                          <button className="pet-delete-btn" type="button" onClick={() => removePet(pet.id)}>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M18 6L6 18M6 6l12 12" />
                            </svg>
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
            )}
          </>
        )}
      </div>
    </section>
  )
}
