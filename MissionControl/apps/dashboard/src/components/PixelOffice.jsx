import React, { useRef, useEffect, useCallback, useState } from 'react'
import { MapPin } from 'lucide-react'
import { OfficeState } from './pixel-engine/engine/officeState'
import { startGameLoop } from './pixel-engine/engine/gameLoop'
import { renderFrame } from './pixel-engine/engine/renderer'
import { loadAllAssets } from './pixel-engine/browserAssetLoader'
import {
  ZOOM_MIN,
  ZOOM_MAX,
  ZOOM_DEFAULT_DPR_FACTOR,
  ZOOM_SCROLL_THRESHOLD,
  PAN_MARGIN_FRACTION,
  CAMERA_FOLLOW_LERP,
  CAMERA_FOLLOW_SNAP_THRESHOLD,
} from './constants'

const TILE_SIZE = 16

/**
 * PixelOffice — Canvas-rendered pixel art office for the Mission Control dashboard.
 * Loads all pixel assets, initializes the game engine, and renders the office scene.
 * Maps dashboard agent data into the pixel engine's character system.
 */
export function PixelOffice({ agents = [] }) {
  const canvasRef = useRef(null)
  const containerRef = useRef(null)
  const officeStateRef = useRef(null)
  const panRef = useRef({ x: 0, y: 0 })
  const zoomRef = useRef(Math.round(ZOOM_DEFAULT_DPR_FACTOR * (window.devicePixelRatio || 1)))
  const stopLoopRef = useRef(null)
  const [loading, setLoading] = useState(true)
  const [zoom, setZoom] = useState(zoomRef.current)
  const agentMapRef = useRef(new Map()) // track which agents are added

  // Middle-mouse pan state
  const isPanningRef = useRef(false)
  const panStartRef = useRef({ mouseX: 0, mouseY: 0, panX: 0, panY: 0 })
  const zoomAccumulatorRef = useRef(0)

  const clampPan = useCallback((px, py) => {
    const canvas = canvasRef.current
    const os = officeStateRef.current
    if (!canvas || !os) return { x: px, y: py }
    const layout = os.getLayout()
    const z = zoomRef.current
    const mapW = layout.cols * TILE_SIZE * z
    const mapH = layout.rows * TILE_SIZE * z
    const marginX = canvas.width * PAN_MARGIN_FRACTION
    const marginY = canvas.height * PAN_MARGIN_FRACTION
    const maxPanX = mapW / 2 + canvas.width / 2 - marginX
    const maxPanY = mapH / 2 + canvas.height / 2 - marginY
    return {
      x: Math.max(-maxPanX, Math.min(maxPanX, px)),
      y: Math.max(-maxPanY, Math.min(maxPanY, py)),
    }
  }, [])

  // Resize canvas to match container
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return
    const rect = container.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1
    const w = Math.round(rect.width * dpr)
    const h = Math.round(rect.height * dpr)
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w
      canvas.height = h
    }
  }, [])

  // Phase 1: Load assets only (no canvas needed)
  useEffect(() => {
    let cancelled = false

    async function loadAssets() {
      const { layout } = await loadAllAssets('/pixel-assets')
      if (cancelled) return
      const officeState = new OfficeState(layout || undefined)
      officeStateRef.current = officeState
      setLoading(false)
    }

    loadAssets().catch(err => {
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
  }, [])

  // Phase 2: Start game loop once canvas is in the DOM (after loading=false)
  useEffect(() => {
    if (loading) return
    const officeState = officeStateRef.current
    if (!officeState) return

    resizeCanvas()
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.imageSmoothingEnabled = false

    const stop = startGameLoop(canvas, {
      update: (dt) => officeState.update(dt),
      render: (ctx2d) => {
        const z = zoomRef.current
        const cw = canvas.width
        const ch = canvas.height
        const layout = officeState.getLayout()

        // Camera follow for selected agent
        if (officeState.cameraFollowId !== null) {
          const followCh = officeState.characters.get(officeState.cameraFollowId)
          if (followCh) {
            const mapW = layout.cols * TILE_SIZE * z
            const mapH = layout.rows * TILE_SIZE * z
            const targetX = -(followCh.x * z - cw / 2 + mapW / 2 - (layout.cols * TILE_SIZE * z) / 2)
            const targetY = -(followCh.y * z - ch / 2 + mapH / 2 - (layout.rows * TILE_SIZE * z) / 2)
            const dx = targetX - panRef.current.x
            const dy = targetY - panRef.current.y
            if (Math.abs(dx) > CAMERA_FOLLOW_SNAP_THRESHOLD || Math.abs(dy) > CAMERA_FOLLOW_SNAP_THRESHOLD) {
              panRef.current.x += dx * CAMERA_FOLLOW_LERP
              panRef.current.y += dy * CAMERA_FOLLOW_LERP
            }
          }
        }

        // Convert characters Map to array for renderer
        const charsArray = Array.from(officeState.characters.values())

        // Build selection state
        const selection = {
          selectedAgentId: officeState.selectedAgentId,
          hoveredAgentId: officeState.hoveredAgentId,
          hoveredTile: officeState.hoveredTile,
          seats: officeState.seats,
          characters: officeState.characters,
        }

        renderFrame(
          ctx2d,
          cw,
          ch,
          officeState.tileMap,
          officeState.furniture,
          charsArray,
          z,
          panRef.current.x,
          panRef.current.y,
          selection,
          undefined, // editor state
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
  }, [loading, resizeCanvas])

  // Handle window resize
  useEffect(() => {
    const onResize = () => resizeCanvas()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [resizeCanvas])

  // Sync dashboard agents into the pixel engine
  useEffect(() => {
    const os = officeStateRef.current
    if (!os) return

    const currentIds = new Set()

    agents.forEach((agent, index) => {
      const id = index
      currentIds.add(id)

      if (!os.characters.has(id)) {
        // Add new agent
        os.addAgent(id, undefined, undefined, undefined, false, agent.display_name || agent.name || '')
        agentMapRef.current.set(id, agent.agent_id)
      }

      // Update agent activity state
      const ch = os.characters.get(id)
      if (ch) {
        const isActive = agent.state !== 'idle'
        if (ch.isActive !== isActive) {
          os.setAgentActive(id, isActive)
        }
        // Map agent state to tool for animation
        if (isActive) {
          const tool = ['planning', 'researching'].includes(agent.state) ? 'Read' : 'Write'
          if (ch.currentTool !== tool) {
            os.setAgentTool(id, tool)
          }
        } else if (ch.currentTool) {
          os.setAgentTool(id, null)
        }
        // Update name
        if (ch.name !== (agent.display_name || agent.name || '')) {
          ch.name = agent.display_name || agent.name || ''
        }
      }
    })

    // Remove agents that no longer exist
    for (const [id] of os.characters) {
      if (id >= 0 && !currentIds.has(id)) {
        os.removeAgent(id)
        agentMapRef.current.delete(id)
      }
    }
  }, [agents])

  // Mouse handlers for zoom + pan
  const handleWheel = useCallback((e) => {
    e.preventDefault()
    zoomAccumulatorRef.current += e.deltaY
    if (Math.abs(zoomAccumulatorRef.current) >= ZOOM_SCROLL_THRESHOLD) {
      const delta = zoomAccumulatorRef.current < 0 ? 1 : -1
      zoomAccumulatorRef.current = 0
      const newZoom = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoomRef.current + delta))
      if (newZoom !== zoomRef.current) {
        zoomRef.current = newZoom
        setZoom(newZoom)
      }
    }
  }, [])

  const handleMouseDown = useCallback((e) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      // Middle-click or Alt+click for panning
      e.preventDefault()
      isPanningRef.current = true
      panStartRef.current = {
        mouseX: e.clientX,
        mouseY: e.clientY,
        panX: panRef.current.x,
        panY: panRef.current.y,
      }
    } else if (e.button === 0) {
      // Left click - hit test agents
      const os = officeStateRef.current
      const canvas = canvasRef.current
      if (!os || !canvas) return

      const rect = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      const z = zoomRef.current
      const layout = os.getLayout()
      const mapW = layout.cols * TILE_SIZE * z
      const mapH = layout.rows * TILE_SIZE * z
      const ox = (canvas.width / 2 - mapW / 2) + panRef.current.x
      const oy = (canvas.height / 2 - mapH / 2) + panRef.current.y

      const canvasX = (e.clientX - rect.left) * dpr
      const canvasY = (e.clientY - rect.top) * dpr
      const worldX = (canvasX - ox) / z
      const worldY = (canvasY - oy) / z

      // Check character hit boxes
      let clickedId = null
      for (const ch of os.characters.values()) {
        const halfW = 8
        const hitH = 24
        if (worldX >= ch.x - halfW && worldX <= ch.x + halfW &&
            worldY >= ch.y - hitH && worldY <= ch.y) {
          clickedId = ch.id
          break
        }
      }

      if (clickedId !== null) {
        os.selectedAgentId = clickedId
        os.cameraFollowId = clickedId
      } else {
        os.selectedAgentId = null
        os.cameraFollowId = null
      }
    }
  }, [])

  const handleMouseMove = useCallback((e) => {
    if (isPanningRef.current) {
      const dpr = window.devicePixelRatio || 1
      const dx = (e.clientX - panStartRef.current.mouseX) * dpr
      const dy = (e.clientY - panStartRef.current.mouseY) * dpr
      const clamped = clampPan(panStartRef.current.panX + dx, panStartRef.current.panY + dy)
      panRef.current.x = clamped.x
      panRef.current.y = clamped.y
    } else {
      // Hover detection for agents
      const os = officeStateRef.current
      const canvas = canvasRef.current
      if (!os || !canvas) return

      const rect = canvas.getBoundingClientRect()
      const dpr = window.devicePixelRatio || 1
      const z = zoomRef.current
      const layout = os.getLayout()
      const mapW = layout.cols * TILE_SIZE * z
      const mapH = layout.rows * TILE_SIZE * z
      const ox = (canvas.width / 2 - mapW / 2) + panRef.current.x
      const oy = (canvas.height / 2 - mapH / 2) + panRef.current.y

      const canvasX = (e.clientX - rect.left) * dpr
      const canvasY = (e.clientY - rect.top) * dpr
      const worldX = (canvasX - ox) / z
      const worldY = (canvasY - oy) / z

      let hoveredId = null
      for (const ch of os.characters.values()) {
        const halfW = 8
        const hitH = 24
        if (worldX >= ch.x - halfW && worldX <= ch.x + halfW &&
            worldY >= ch.y - hitH && worldY <= ch.y) {
          hoveredId = ch.id
          break
        }
      }
      os.hoveredAgentId = hoveredId
    }
  }, [clampPan])

  const handleMouseUp = useCallback(() => {
    isPanningRef.current = false
  }, [])

  // Prevent context menu on canvas
  const handleContextMenu = useCallback((e) => e.preventDefault(), [])

  return (
    <section
      className="panel iso-room-panel"
      style={{
        flex: 1,
        minHeight: '400px',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        overflow: 'hidden',
        borderRadius: '12px',
        background: '#0a0f1c',
        border: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      {/* HUD Header */}
      <div
        style={{
          position: 'absolute',
          top: 16,
          left: 20,
          zIndex: 10,
        }}
      >
        <div
          style={{
            marginBottom: 0,
            fontSize: '11px',
            letterSpacing: '0.1em',
            fontWeight: 600,
            color: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <MapPin size={12} style={{ marginRight: '6px', color: '#3b82f6' }} />
          THE OFFICE
        </div>
      </div>

      {/* Canvas Container */}
      <div
        ref={containerRef}
        style={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
          cursor: isPanningRef.current ? 'grabbing' : 'grab',
        }}
      >
        {loading ? (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'rgba(255,255,255,0.4)',
              fontSize: '12px',
            }}
          >
            Cargando oficina virtual...
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            style={{
              width: '100%',
              height: '100%',
              display: 'block',
              imageRendering: 'pixelated',
            }}
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onContextMenu={handleContextMenu}
          />
        )}
      </div>

      {/* Zoom Controls */}
      <div
        style={{
          position: 'absolute',
          top: 16,
          right: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          zIndex: 10,
        }}
      >
        <button
          onClick={() => {
            const newZoom = Math.min(ZOOM_MAX, zoomRef.current + 1)
            zoomRef.current = newZoom
            setZoom(newZoom)
          }}
          style={{
            background: 'rgba(15,23,42,0.85)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: 'white',
            width: 28,
            height: 28,
            borderRadius: 4,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            fontWeight: 'bold',
          }}
        >
          +
        </button>
        <div
          style={{
            background: 'rgba(15,23,42,0.7)',
            color: 'rgba(255,255,255,0.5)',
            fontSize: '9px',
            textAlign: 'center',
            padding: '2px 0',
            borderRadius: 2,
          }}
        >
          {zoom}x
        </div>
        <button
          onClick={() => {
            const newZoom = Math.max(ZOOM_MIN, zoomRef.current - 1)
            zoomRef.current = newZoom
            setZoom(newZoom)
          }}
          style={{
            background: 'rgba(15,23,42,0.85)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: 'white',
            width: 28,
            height: 28,
            borderRadius: 4,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '14px',
            fontWeight: 'bold',
          }}
        >
          -
        </button>
      </div>

      {/* Vignette overlay for depth */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse at center, transparent 60%, rgba(10, 15, 28, 0.6) 100%)',
          pointerEvents: 'none',
          zIndex: 5,
        }}
      />
    </section>
  )
}
