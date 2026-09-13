import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './ScanLine.module.css';

export function ScanLine({ isScanning = false, className = '' }) {
  const reducedMotion = useReducedMotion();

  if (!isScanning) return null;

  return (
    <div className={`${styles.scanContainer} ${className}`}>
      <div className={styles.meshGrid} />

      {!reducedMotion ? (
        <motion.div
          className={styles.sweepLine}
          initial={{ top: '0%' }}
          animate={{ top: ['0%', '100%', '0%'] }}
          transition={{ repeat: Infinity, duration: 2.4, ease: 'easeInOut' }}
        />
      ) : (
        <div className={styles.sweepLine} style={{ top: '50%' }} />
      )}
    </div>
  );
}
