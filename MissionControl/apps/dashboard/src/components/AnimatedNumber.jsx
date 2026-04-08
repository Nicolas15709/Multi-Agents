import { useEffect, useRef } from 'react'
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'

export function AnimatedNumber({ value, duration = 0.6, className }) {
  const motionVal = useMotionValue(0)
  const rounded = useTransform(motionVal, v => Math.round(v))
  const prevRef = useRef(0)

  useEffect(() => {
    const from = prevRef.current
    prevRef.current = value
    const controls = animate(motionVal, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
    })
    return () => controls.stop()
  }, [value, duration, motionVal])

  return <motion.span className={className}>{rounded}</motion.span>
}
