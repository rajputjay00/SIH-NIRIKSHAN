import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useT } from '../../i18n/useT';
import styles from './StatusDot.module.css';

export function StatusDot({ isOnline = true, showText = true, className = '' }) {
  const reducedMotion = useReducedMotion();
  const { t } = useT();

  const dotClass = isOnline ? styles.healthy : styles.unhealthy;
  const statusLabel = isOnline ? t('status_online') : t('status_offline');

  return (
    <div className={`${styles.statusWrapper} ${className}`}>
      <motion.span
        className={`${styles.dot} ${dotClass}`}
        animate={isOnline && !reducedMotion ? { scale: [1, 1.25, 1], opacity: [1, 0.7, 1] } : {}}
        transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
      />
      {showText && <span>{statusLabel}</span>}
    </div>
  );
}
