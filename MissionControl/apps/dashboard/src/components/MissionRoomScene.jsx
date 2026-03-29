import { useMemo, useRef, Suspense } from 'react'
import { Canvas, useFrame, useLoader } from '@react-three/fiber'
import { OrthographicCamera, Html, OrbitControls } from '@react-three/drei'
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader'
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader'
import * as THREE from 'three'
import { motion } from 'framer-motion'
import { Activity, MapPin } from 'lucide-react'

/* ─── WORKSTATION POSITIONS (isometric grid) ─── */
const WORKSTATIONS = [
  { id: 'agent-0', pos: [-3, 0, -2], label: 'Centro de Mando' },
  { id: 'agent-1', pos: [3, 0, -1], label: 'Investigación' },
  { id: 'agent-2', pos: [-2, 0, 3], label: 'Diseño' },
  { id: 'agent-3', pos: [2, 0, 3], label: 'Desarrollo' },
  { id: 'agent-4', pos: [0, 0, -4], label: 'QA' },
]

/* ─── OBJ Model Loader ─── */
function OfficeModel({ objPath, mtlPath, position = [0, 0, 0], rotation = [0, 0, 0], scale = 1 }) {
  const materials = useLoader(MTLLoader, mtlPath)
  const obj = useLoader(OBJLoader, objPath, (loader) => {
    materials.preload()
    loader.setMaterials(materials)
  })

  const cloned = useMemo(() => {
    const clone = obj.clone()
    clone.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = true
        child.receiveShadow = true
      }
    })
    return clone
  }, [obj])

  return <primitive object={cloned} position={position} rotation={rotation} scale={scale} />
}

/* ─── Procedural Floor ─── */
function Floor() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
      <planeGeometry args={[20, 20]} />
      <meshStandardMaterial color="#1a1f2e" roughness={0.9} metalness={0.1} />
    </mesh>
  )
}

/* ─── Floor Grid Lines ─── */
function FloorGrid() {
  return (
    <gridHelper args={[20, 20, '#1e2638', '#151a28']} position={[0, 0.001, 0]} />
  )
}

/* ─── Procedural Desk ─── */
function Desk({ position = [0, 0, 0], rotation = [0, 0, 0] }) {
  return (
    <group position={position} rotation={rotation}>
      {/* Table Top */}
      <mesh position={[0, 0.72, 0]} castShadow receiveShadow>
        <boxGeometry args={[1.4, 0.05, 0.7]} />
        <meshStandardMaterial color="#2a3142" roughness={0.5} metalness={0.3} />
      </mesh>
      {/* Leg 1 */}
      <mesh position={[-0.6, 0.35, -0.25]} castShadow>
        <boxGeometry args={[0.04, 0.7, 0.04]} />
        <meshStandardMaterial color="#404858" roughness={0.7} />
      </mesh>
      {/* Leg 2 */}
      <mesh position={[0.6, 0.35, -0.25]} castShadow>
        <boxGeometry args={[0.04, 0.7, 0.04]} />
        <meshStandardMaterial color="#404858" roughness={0.7} />
      </mesh>
      {/* Leg 3 */}
      <mesh position={[-0.6, 0.35, 0.25]} castShadow>
        <boxGeometry args={[0.04, 0.7, 0.04]} />
        <meshStandardMaterial color="#404858" roughness={0.7} />
      </mesh>
      {/* Leg 4 */}
      <mesh position={[0.6, 0.35, 0.25]} castShadow>
        <boxGeometry args={[0.04, 0.7, 0.04]} />
        <meshStandardMaterial color="#404858" roughness={0.7} />
      </mesh>
      {/* Monitor */}
      <mesh position={[0, 1.05, -0.15]} castShadow>
        <boxGeometry args={[0.6, 0.4, 0.03]} />
        <meshStandardMaterial color="#0a0e1a" roughness={0.2} metalness={0.5} emissive="#1a2040" emissiveIntensity={0.5} />
      </mesh>
      {/* Monitor Stand */}
      <mesh position={[0, 0.85, -0.15]} castShadow>
        <boxGeometry args={[0.08, 0.2, 0.08]} />
        <meshStandardMaterial color="#404858" roughness={0.7} />
      </mesh>
      {/* Keyboard */}
      <mesh position={[0, 0.76, 0.1]} castShadow>
        <boxGeometry args={[0.4, 0.015, 0.15]} />
        <meshStandardMaterial color="#2a2f3e" roughness={0.6} metalness={0.2} />
      </mesh>
    </group>
  )
}

/* ─── Office Chair (procedural) ─── */
function Chair({ position = [0, 0, 0], rotation = [0, 0, 0] }) {
  return (
    <group position={position} rotation={rotation}>
      {/* Seat */}
      <mesh position={[0, 0.42, 0]} castShadow>
        <boxGeometry args={[0.45, 0.06, 0.45]} />
        <meshStandardMaterial color="#1e2432" roughness={0.7} />
      </mesh>
      {/* Backrest */}
      <mesh position={[0, 0.7, -0.2]} castShadow>
        <boxGeometry args={[0.43, 0.5, 0.04]} />
        <meshStandardMaterial color="#1e2432" roughness={0.7} />
      </mesh>
      {/* Center Pole */}
      <mesh position={[0, 0.22, 0]} castShadow>
        <cylinderGeometry args={[0.03, 0.03, 0.4]} />
        <meshStandardMaterial color="#555" roughness={0.5} metalness={0.6} />
      </mesh>
      {/* Base */}
      <mesh position={[0, 0.03, 0]} castShadow>
        <cylinderGeometry args={[0.22, 0.22, 0.02]} />
        <meshStandardMaterial color="#555" roughness={0.5} metalness={0.6} />
      </mesh>
    </group>
  )
}

/* ─── Wall Partitions ─── */
function WallPartition({ position = [0, 0, 0], rotation = [0, 0, 0], width = 3, height = 2.5, color = '#1a2035' }) {
  return (
    <mesh position={position} rotation={rotation} castShadow receiveShadow>
      <boxGeometry args={[width, height, 0.1]} />
      <meshStandardMaterial color={color} roughness={0.8} metalness={0.1} />
    </mesh>
  )
}

/* ─── Decorations: Plant ─── */
function Plant({ position = [0, 0, 0] }) {
  return (
    <group position={position}>
      {/* Pot */}
      <mesh position={[0, 0.2, 0]} castShadow>
        <cylinderGeometry args={[0.15, 0.12, 0.35, 8]} />
        <meshStandardMaterial color="#2d1f14" roughness={0.9} />
      </mesh>
      {/* Leaves cluster */}
      <mesh position={[0, 0.55, 0]}>
        <sphereGeometry args={[0.25, 8, 8]} />
        <meshStandardMaterial color="#1a6b3a" roughness={0.8} />
      </mesh>
    </group>
  )
}

/* ─── Filing Cabinet ─── */
function FilingCabinet({ position = [0, 0, 0], rotation = [0, 0, 0] }) {
  return (
    <mesh position={[position[0], position[1] + 0.6, position[2]]} rotation={rotation} castShadow>
      <boxGeometry args={[0.5, 1.2, 0.4]} />
      <meshStandardMaterial color="#2a3142" roughness={0.6} metalness={0.2} />
    </mesh>
  )
}

/* ─── Sofa ─── */
function Sofa({ position = [0, 0, 0], rotation = [0, 0, 0] }) {
  return (
    <group position={position} rotation={rotation}>
      {/* Base */}
      <mesh position={[0, 0.22, 0]} castShadow>
        <boxGeometry args={[1.5, 0.35, 0.7]} />
        <meshStandardMaterial color="#1e3a28" roughness={0.8} />
      </mesh>
      {/* Back */}
      <mesh position={[0, 0.55, -0.28]} castShadow>
        <boxGeometry args={[1.5, 0.35, 0.15]} />
        <meshStandardMaterial color="#1a5032" roughness={0.8} />
      </mesh>
      {/* Arm Left */}
      <mesh position={[-0.7, 0.45, 0]} castShadow>
        <boxGeometry args={[0.1, 0.5, 0.7]} />
        <meshStandardMaterial color="#1a5032" roughness={0.8} />
      </mesh>
      {/* Arm Right */}
      <mesh position={[0.7, 0.45, 0]} castShadow>
        <boxGeometry args={[0.1, 0.5, 0.7]} />
        <meshStandardMaterial color="#1a5032" roughness={0.8} />
      </mesh>
    </group>
  )
}

/* ─── Whiteboard ─── */
function Whiteboard({ position = [0, 0, 0], rotation = [0, 0, 0] }) {
  return (
    <group position={position} rotation={rotation}>
      <mesh position={[0, 1.5, 0]} castShadow>
        <boxGeometry args={[1.2, 0.8, 0.04]} />
        <meshStandardMaterial color="#e8e8e8" roughness={0.3} metalness={0.05} />
      </mesh>
      {/* Frame */}
      <mesh position={[0, 1.5, -0.025]}>
        <boxGeometry args={[1.24, 0.84, 0.02]} />
        <meshStandardMaterial color="#555" roughness={0.5} metalness={0.3} />
      </mesh>
    </group>
  )
}

/* ─── Floating Agent Label in 3D Space ─── */
function AgentLabel({ agent, position }) {
  const isActive = agent.state !== 'idle'
  const activityLabel = {
    idle: 'Standby', planning: 'Planificando', researching: 'Investigando',
    designing: 'Diseñando', building: 'Construyendo', reviewing: 'Revisando',
  }

  return (
    <Html position={[position[0], 2.2, position[2]]} center distanceFactor={8} zIndexRange={[10, 0]}>
      <div className="agent-3d-label">
        <div className="label-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '5px', marginBottom: '3px' }}>
            <div style={{
              width: '6px', height: '6px', borderRadius: '50%',
              background: isActive ? '#10b981' : '#3b4563',
              boxShadow: isActive ? '0 0 6px #10b981' : 'none',
            }} />
            <div className="label-name">{agent.display_name}</div>
          </div>
          <div className={`label-state ${isActive ? '' : 'idle'}`}>
            {activityLabel[agent.state] || agent.state}
          </div>
          {isActive && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '3px', marginTop: '4px' }}>
              <Activity size={8} style={{ color: '#10b981' }} />
              <span style={{ fontSize: '7px', color: '#6b7fa3' }}>Processing...</span>
            </div>
          )}
        </div>
        <div className="label-connector" />
        <div className="label-dot" />
      </div>
    </Html>
  )
}

/* ─── Glow Ring Under Active Agent Desk ─── */
function GlowRing({ position, isActive }) {
  const ref = useRef()

  useFrame(({ clock }) => {
    if (ref.current && isActive) {
      ref.current.material.opacity = 0.15 + Math.sin(clock.getElapsedTime() * 2) * 0.08
    }
  })

  if (!isActive) return null

  return (
    <mesh ref={ref} position={[position[0], 0.02, position[2]]} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[0.8, 1.2, 32]} />
      <meshBasicMaterial color="#6366f1" transparent opacity={0.15} side={THREE.DoubleSide} />
    </mesh>
  )
}

/* ─── Ambient Particles ─── */
function Particles() {
  const count = 60
  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 16
      pos[i * 3 + 1] = Math.random() * 6 + 0.5
      pos[i * 3 + 2] = (Math.random() - 0.5) * 16
    }
    return pos
  }, [])

  const ref = useRef()
  useFrame(({ clock }) => {
    if (ref.current) {
      const arr = ref.current.geometry.attributes.position.array
      for (let i = 0; i < count; i++) {
        arr[i * 3 + 1] += Math.sin(clock.getElapsedTime() * 0.5 + i) * 0.001
      }
      ref.current.geometry.attributes.position.needsUpdate = true
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={count} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.03} color="#6366f1" transparent opacity={0.4} sizeAttenuation />
    </points>
  )
}

/* ─── THE COMPLETE OFFICE SCENE ─── */
function OfficeScene({ agents = [] }) {
  const agentMap = useMemo(() => {
    const map = {}
    for (const agent of agents) {
      map[agent.agent_id] = agent
    }
    return map
  }, [agents])

  return (
    <>
      {/* Lighting Setup */}
      <ambientLight intensity={0.35} color="#b0c4ff" />
      <directionalLight
        position={[8, 12, 6]}
        intensity={0.8}
        color="#e0e7ff"
        castShadow
        shadow-mapSize={[1024, 1024]}
        shadow-camera-left={-10}
        shadow-camera-right={10}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
      />
      <directionalLight position={[-4, 6, -4]} intensity={0.2} color="#818cf8" />
      <pointLight position={[0, 4, 0]} intensity={0.3} color="#6366f1" distance={12} />

      {/* Floor */}
      <Floor />
      <FloorGrid />

      {/* Back Walls */}
      <WallPartition position={[0, 1.25, -6]} width={14} height={2.5} color="#111827" />
      <WallPartition position={[-7, 1.25, 0]} rotation={[0, Math.PI / 2, 0]} width={12} height={2.5} color="#0f172a" />

      {/* Room Divider Partitions */}
      <WallPartition position={[0, 0.8, -0.5]} width={2} height={1.6} color="#1e293b" />
      <WallPartition position={[5, 0.8, 1]} rotation={[0, Math.PI / 2, 0]} width={3} height={1.6} color="#1e293b" />

      {/* ── Supervisor Station (centro de mando) ──  */}
      <Desk position={[-3, 0, -2]} />
      <Chair position={[-3, 0, -1.2]} rotation={[0, Math.PI, 0]} />
      <Desk position={[-4.5, 0, -2]} />

      {/* ── Researcher Station ── */}
      <Desk position={[3, 0, -1]} rotation={[0, -Math.PI / 6, 0]} />
      <Chair position={[3, 0, -0.2]} rotation={[0, Math.PI + Math.PI / 6, 0]} />

      {/* ── Designer Station ── */}
      <Desk position={[-2, 0, 3]} rotation={[0, Math.PI / 4, 0]} />
      <Chair position={[-2, 0, 3.8]} rotation={[0, Math.PI - Math.PI / 4, 0]} />

      {/* ── Developer Station ── */}
      <Desk position={[2, 0, 3]} rotation={[0, -Math.PI / 4, 0]} />
      <Chair position={[2, 0, 3.8]} rotation={[0, Math.PI + Math.PI / 4, 0]} />
      <Desk position={[3.5, 0, 3.5]} rotation={[0, -Math.PI / 4, 0]} />

      {/* ── QA Station ── */}
      <Desk position={[0, 0, -4]} />
      <Chair position={[0, 0, -3.2]} rotation={[0, Math.PI, 0]} />

      {/* Decorations */}
      <Plant position={[-6, 0, -4.5]} />
      <Plant position={[5.5, 0, -4]} />
      <Plant position={[-5, 0, 4.5]} />
      <Plant position={[5, 0, 5]} />
      
      <FilingCabinet position={[-5.5, 0, -2]} />
      <FilingCabinet position={[-5.5, 0, -1]} />
      <FilingCabinet position={[5.5, 0, -3]} />
      
      <Sofa position={[-4.5, 0, 4]} rotation={[0, Math.PI / 2, 0]} />
      
      <Whiteboard position={[-6.9, 0, -2]} rotation={[0, Math.PI / 2, 0]} />
      <Whiteboard position={[0, 0, -5.9]} />

      {/* Particles */}
      <Particles />

      {/* Agent Labels & Glow Rings */}
      {WORKSTATIONS.map((ws) => {
        const agent = agentMap[ws.id]
        if (!agent) return null
        return (
          <group key={ws.id}>
            <AgentLabel agent={agent} position={ws.pos} />
            <GlowRing position={ws.pos} isActive={agent.state !== 'idle'} />
          </group>
        )
      })}
    </>
  )
}

/* ─── MAIN EXPORT ─── */
export function MissionRoomScene({ agents = [] }) {
  return (
    <section className="panel iso-room-panel" style={{ flex: 1, minHeight: '350px', position: 'relative', overflow: 'hidden' }}>
      <div className="room-overlay-label" style={{ position: 'absolute', top: 12, left: 16, zIndex: 10 }}>
        <div className="section-title" style={{ marginBottom: 0, fontSize: '10px' }}>
          <MapPin size={10} /> La Oficina Virtual
        </div>
      </div>

      <div className="room-canvas-wrapper" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
        <Canvas shadows dpr={[1, 2]} style={{ background: 'transparent' }}>
          <OrthographicCamera
            makeDefault
            position={[10, 10, 10]}
            zoom={45}
            near={-100}
            far={100}
          />
          <OrbitControls target={[0, 0, 0]} enablePan={true} enableZoom={true} enableRotate={true} />
          <Suspense fallback={null}>
            <OfficeScene agents={agents} />
          </Suspense>
        </Canvas>
      </div>
    </section>
  )
}
