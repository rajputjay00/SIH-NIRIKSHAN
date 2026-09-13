import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './Logo.module.css';

export function Logo({ size = 32, animate = false, variant = 'blue', className = '' }) {
  const reducedMotion = useReducedMotion();
  const shouldAnimate = animate && !reducedMotion;

  const strokeColor = variant === 'tricolour' ? 'var(--saffron)' : 'var(--blue-500)';

  return (
    <div className={`${styles.logoContainer} ${className}`} style={{ width: size, height: size }}>
      <svg
        className={styles.logoSvg}
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Outer Arc */}
        <motion.path
          d="M 20,50 A 30,30 0 1,1 80,50"
          stroke={strokeColor}
          strokeWidth="6"
          strokeLinecap="round"
          initial={shouldAnimate ? { pathLength: 0 } : { pathLength: 1 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />

        {/* Magnifying Glass Outer Circle */}
        <motion.circle
          cx="50"
          cy="45"
          r="26"
          stroke="var(--navy-900)"
          strokeWidth="6"
          fill="none"
          initial={shouldAnimate ? { scale: 0.8, opacity: 0 } : { scale: 1, opacity: 1 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        />

        {/* Package Box inside */}
        <motion.rect
          x="38"
          y="33"
          width="24"
          height="24"
          rx="3"
          fill="var(--navy-900)"
          initial={shouldAnimate ? { y: 45, opacity: 0 } : { y: 33, opacity: 1 }}
          animate={{ y: 33, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.5 }}
        />

        {/* Check Badge Pop */}
        <motion.circle
          cx="68"
          cy="60"
          r="10"
          fill="var(--pass)"
          initial={shouldAnimate ? { scale: 0 } : { scale: 1 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 12, delay: 0.8 }}
        />

        {/* Checkmark in Badge */}
        <motion.path
          d="M 63,60 L 66,63 L 73,56"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={shouldAnimate ? { pathLength: 0 } : { pathLength: 1 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.3, delay: 0.9 }}
        />
      </svg>
    </div>
  );
}
