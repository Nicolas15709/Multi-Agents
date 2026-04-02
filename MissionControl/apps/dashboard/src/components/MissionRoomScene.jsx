import React, { useMemo, useState } from 'react'
import { MapPin, Activity } from 'lucide-react'
import { PixelAgent } from './PixelAgent'

/* ─── WORKSTATION POSITIONS (2D Isometric/Grid) ───
   Mapped to pixel coordinates (x, y) relative to the center of the room.
*/
const WORKSTATIONS = [
  { id: 'agent-0', label: 'Centro de Mando', pos: { x: 0, y: 50 }, facing: 'down', charIndex: 0 },
  { id: 'agent-1', label: 'Investigación', pos: { x: -150, y: -50 }, facing: 'right', charIndex: 1 },
  { id: 'agent-2', label: 'Diseño', pos: { x: 150, y: -50 }, facing: 'left', charIndex: 2 },
  { id: 'agent-3', label: 'Desarrollo', pos: { x: -100, y: 150 }, facing: 'up', charIndex: 3 },
  { id: 'agent-4', label: 'QA', pos: { x: 100, y: 150 }, facing: 'up', charIndex: 4 },
]

export function MissionRoomScene({ agents = [] }) {
  const [zoom, setZoom] = useState(1);

  // Map backend agents to workstations
  const agentMap = useMemo(() => {
    const map = {}
    for (const agent of agents) {
      map[agent.agent_id] = agent
    }
    return map
  }, [agents])

  return (
    <section className="panel iso-room-panel" style={{ flex: 1, minHeight: '400px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden', borderRadius: '12px', background: '#0a0f1c', border: '1px solid rgba(255,255,255,0.05)' }}>
      {/* HUD Header */}
      <div className="room-overlay-label" style={{ position: 'absolute', top: 16, left: 20, zIndex: 10 }}>
        <div className="section-title" style={{ marginBottom: 0, fontSize: '11px', letterSpacing: '0.1em', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center' }}>
          <MapPin size={12} style={{ marginRight: '6px', color: '#3b82f6' }} /> PIXEL HQ (2D)
        </div>
      </div>

      {/* 2D Grid Container */}
      <div 
        className="canvas-2d-container" 
        style={{ 
          flex: 1, 
          position: 'relative', 
          overflow: 'hidden',
          backgroundImage: `
            linear-gradient(rgba(59, 130, 246, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59, 130, 246, 0.05) 1px, transparent 1px)
          `,
          backgroundSize: '32px 32px',
          backgroundPosition: 'center center',
          cursor: 'grab'
        }}
      >
        {/* Centered Map Area where coordinates (0,0) are the true center */}
        <div 
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: 0,
            height: 0,
            transform: `scale(${zoom})`,
            transformOrigin: 'center center',
            transition: 'transform 0.2s ease-out'
          }}
        >
          {/* Render Workstations and Agents */}
          {WORKSTATIONS.map((ws) => {
            const agent = agentMap[ws.id]
            
            // Map agent.state to pixel agent animation
            let animationState = 'idle'
            if (agent && agent.state !== 'idle') {
              animationState = ['planning', 'researching'].includes(agent.state) ? 'read' : 'type'
            }

            // Fallback for empty desk if no active agent connected
            const isActive = !!agent && agent.state !== 'idle'

            return (
              <div 
                key={ws.id} 
                className="workstation"
                style={{
                  position: 'absolute',
                  left: ws.pos.x,
                  top: ws.pos.y,
                  width: '64px', // Space for desk and character
                  height: '64px',
                  // Origin offset so the character's feet match the coordinate exactly
                  transform: 'translate(-50%, -100%)',
                  zIndex: Math.round(ws.pos.y) // Y-sorting so agents in front overlap those in back
                }}
              >
                {/* Simulated Rug / Base Shadow under the agent */}
                <div style={{
                     position: 'absolute',
                     bottom: 0,
                     left: '50%',
                     transform: 'translate(-50%, 50%)', // Centered exactly at the feet [x, y]
                     width: '48px',
                     height: '24px',
                     background: isActive ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                     borderRadius: '50%',
                     boxShadow: isActive ? '0 0 15px rgba(59, 130, 246, 0.4)' : 'none',
                     transition: 'all 0.3s'
                }}/>
                
                {/* The Agent Avatar (Assuming PixelAgent anchors bottom-center correctly!) */}
                <PixelAgent 
                  charIndex={ws.charIndex} 
                  direction={ws.facing} 
                  state={animationState} 
                  scale={2} 
                  x={32} // Center of the workstation div
                  y={64} // Bottom of the workstation div
                />

                {/* Floating Name Label */}
                <div style={{
                  position: 'absolute',
                  top: -20,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'rgba(15, 23, 42, 0.8)',
                  backdropFilter: 'blur(4px)',
                  padding: '4px 8px',
                  borderRadius: '4px',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#fff',
                  fontSize: '9px',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  zIndex: 100
                }}>
                  {isActive && <Activity size={10} color="#3b82f6" className="pulse-icon" />}
                  {agent ? agent.name : ws.label}
                </div>
              </div>
            )
          })}
        </div>
      </div>
      
      {/* Zoom Controls Overlay */}
      <div style={{ position: 'absolute', bottom: 16, right: 20, display: 'flex', gap: '8px', zIndex: 10 }}>
        <button 
          onClick={() => setZoom(z => Math.max(0.5, z - 0.2))}
          style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', width: 28, height: 28, borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >-</button>
        <button 
          onClick={() => setZoom(z => Math.min(2, z + 0.2))}
          style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', width: 28, height: 28, borderRadius: 6, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >+</button>
      </div>
    </section>
  )
}
