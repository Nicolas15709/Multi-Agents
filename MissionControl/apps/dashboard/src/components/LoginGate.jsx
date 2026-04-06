import { TerminalSquare } from 'lucide-react'
import { loadOfficeConfig } from './OfficeCustomizer'

export function LoginGate() {
  const { name } = loadOfficeConfig()
  return (
    <div className="loading-screen" style={{ background: 'var(--bg)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
      <div className="panel" style={{ padding: '40px', maxWidth: '400px', width: '100%', textAlign: 'center', background: 'var(--panel)', border: '1px solid var(--panel-border)' }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
          <TerminalSquare size={48} color="var(--accent-2)" />
        </div>
        <p className="eyebrow" style={{ marginBottom: '8px' }}>Security Clearance Required</p>
        <h1 className="mission-title" style={{ fontSize: '1.8rem', marginBottom: '16px' }}>{name}</h1>
        <p className="muted" style={{ fontSize: '13px', lineHeight: 1.5, marginBottom: '32px' }}>
          AutentÃ­quese para acceder a la sala de mando interactiva y al ecosistema de agentes.
        </p>
        <button 
          className="login-button" 
          type="button" 
          style={{ 
            width: '100%', 
            padding: '12px', 
            borderRadius: 'var(--radius-sm)', 
            background: 'var(--accent-2)', 
            color: 'white', 
            fontWeight: 700, 
            border: 'none', 
            cursor: 'pointer',
            transition: 'background 0.3s ease' 
          }}
          onMouseOver={(e) => e.currentTarget.style.background = '#4f46e5'}
          onMouseOut={(e) => e.currentTarget.style.background = 'var(--accent-2)'}
        >
          Verify Credentials (Simulated)
        </button>
      </div>
    </div>
  )
}

