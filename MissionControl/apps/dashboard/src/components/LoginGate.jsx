import { useState } from 'react'
import { TerminalSquare, Loader2, AlertCircle, Eye, EyeOff } from 'lucide-react'
import { loadOfficeConfig } from './OfficeCustomizer'
import { resolveApiBaseUrl, setAuthToken } from '../runtimeApi'

export function LoginGate({ onLogin }) {
  const { name, color } = loadOfficeConfig()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!username.trim() || !password) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${resolveApiBaseUrl()}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok || !json.token) {
        const msg = json.error === 'invalid_credentials'
          ? 'Usuario o contraseña incorrectos'
          : json.error === 'auth_not_configured'
          ? 'Auth no configurada — revisa MISSION_CONTROL_JWT_SECRET y MISSION_CONTROL_DASHBOARD_PASSWORD en tu .env'
          : json.error === 'rate_limit_exceeded'
          ? 'Demasiados intentos. Espera un momento.'
          : 'Error de conexión con el servidor'
        setError(msg)
        return
      }
      setAuthToken(json.token)
      onLogin(json.token)
    } catch {
      setError('No se pudo conectar con el servidor. ¿Está corriendo el backend?')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: '8px',
    color: 'var(--text-bright)',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.2s',
  }

  const labelStyle = {
    display: 'block',
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.06em',
    color: 'var(--muted)',
    textTransform: 'uppercase',
    marginBottom: '6px',
  }

  return (
    <div
      className="loading-screen"
      style={{
        background: 'var(--bg)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        gap: '24px',
      }}
    >
      {/* Brand mark */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
        <div
          style={{
            width: 52,
            height: 52,
            borderRadius: 14,
            background: `${color}22`,
            border: `1px solid ${color}44`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <TerminalSquare size={26} color={color} />
        </div>
        <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em' }}>
          {name}
        </div>
        <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
          Acceso al sistema de misiones
        </div>
      </div>

      {/* Login card */}
      <div
        style={{
          width: '100%',
          maxWidth: 360,
          background: 'var(--panel)',
          border: '1px solid var(--panel-border)',
          borderRadius: '14px',
          padding: '28px 24px',
        }}
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Error */}
          {error && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                padding: '10px 12px',
                background: 'rgba(239,68,68,0.12)',
                border: '1px solid rgba(239,68,68,0.25)',
                borderRadius: '8px',
                fontSize: '13px',
                color: '#f87171',
                lineHeight: 1.4,
              }}
            >
              <AlertCircle size={14} style={{ marginTop: 2, flexShrink: 0 }} />
              {error}
            </div>
          )}

          {/* Username */}
          <div>
            <label style={labelStyle}>Usuario</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="admin"
              autoComplete="username"
              disabled={loading}
              required
              style={inputStyle}
              onFocus={(e) => (e.target.style.borderColor = color)}
              onBlur={(e) => (e.target.style.borderColor = 'rgba(255,255,255,0.10)')}
            />
          </div>

          {/* Password */}
          <div>
            <label style={labelStyle}>Contraseña</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                disabled={loading}
                required
                style={{ ...inputStyle, paddingRight: '40px' }}
                onFocus={(e) => (e.target.style.borderColor = color)}
                onBlur={(e) => (e.target.style.borderColor = 'rgba(255,255,255,0.10)')}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                style={{
                  position: 'absolute',
                  right: 10,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--muted)',
                  padding: 4,
                  display: 'flex',
                }}
                tabIndex={-1}
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || !username.trim() || !password}
            style={{
              width: '100%',
              padding: '11px',
              borderRadius: '9px',
              background: loading || !username.trim() || !password ? 'rgba(255,255,255,0.06)' : color,
              color: loading || !username.trim() || !password ? 'var(--muted)' : 'white',
              fontWeight: 700,
              fontSize: '14px',
              border: 'none',
              cursor: loading || !username.trim() || !password ? 'not-allowed' : 'pointer',
              transition: 'background 0.2s, color 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
            }}
          >
            {loading && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
            {loading ? 'Verificando...' : 'Ingresar'}
          </button>
        </form>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        input::placeholder { color: rgba(255,255,255,0.2); }
      `}</style>
    </div>
  )
}
