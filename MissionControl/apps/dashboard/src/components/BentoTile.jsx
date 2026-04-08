import { useRef, useState, useCallback } from 'react'
import { motion } from 'framer-motion'

export const bentoContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.1 } },
}

export const bentoItem = {
  hidden: { opacity: 0, y: 16, scale: 0.97 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 300, damping: 24 },
  },
}

export function BentoTile({ children, className = '', style, ariaLabel }) {
  const ref = useRef(null)
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 })

  const handleMouseMove = useCallback((e) => {
    const rect = ref.current?.getBoundingClientRect()
    if (!rect) return
    setMousePos({
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
    })
  }, [])

  return (
    <motion.div
      ref={ref}
      className={`bento-tile ${className}`}
      style={style}
      variants={bentoItem}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setMousePos({ x: 0.5, y: 0.5 })}
      whileHover={{ scale: 1.005 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      role="region"
      aria-label={ariaLabel}
    >
      <div
        className="bento-tile-spotlight"
        style={{
          background: `radial-gradient(300px circle at ${mousePos.x * 100}% ${mousePos.y * 100}%, rgba(124,106,239,0.06), transparent 60%)`,
        }}
      />
      {children}
    </motion.div>
  )
}
