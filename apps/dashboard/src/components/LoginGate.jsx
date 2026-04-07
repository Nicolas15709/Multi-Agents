import { motion } from 'framer-motion';
import { ShieldCheck, ArrowRight } from 'lucide-react';

export function LoginGate({ onLogin }) {
  return (
    <div className="login-gate">
      <motion.div 
        className="login-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <div className="avatar-container" style={{ margin: '0 auto 24px auto', width: 64, height: 64 }}>
           <div className="avatar" style={{ width: '100%', height: '100%', borderRadius: '18px' }}>
              <ShieldCheck size={32} />
           </div>
        </div>
        
        <p className="section-title">Security Protocol</p>
        <h1 style={{ fontSize: '2.5rem', margin: '8px 0', letterSpacing: '-0.02em' }}>VIRTUAL AGENCY</h1>
        <p className="muted" style={{ maxWidth: '300px', margin: '0 auto 32px auto' }}>
          Plataforma de Operaciones de Marketing AutÃ³nomo. Ingrese con sus credenciales de agencia.
        </p>
        
        <motion.button 
          whileHover={{ scale: 1.02, backgroundColor: 'rgba(99, 102, 241, 0.2)' }}
          whileTap={{ scale: 0.98 }}
          className="login-button" 
          type="button"
          onClick={onLogin}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', width: '100%' }}
        >
          Continuar al Sistema <ArrowRight size={18} />
        </motion.button>
        
        <div style={{ marginTop: '24px', fontSize: '11px', color: 'rgba(255,255,255,0.3)' }}>
          Powered by AntiGravity Multi-Agent Runtimes
        </div>
      </motion.div>
    </div>
  )
}

