import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './Chip.module.css';

export function Chip({ children, selected = false, onClick, className = '', icon: Icon }) {
  const reducedMotion = useReducedMotion();

  return (
    <motion.button
      type="button"
      onClick={onClick}
      className={`${styles.chip} ${selected ? styles.selected : ''} ${className}`}
      whileTap={reducedMotion ? {} : { scale: 0.95 }}
    >
      {Icon && <Icon size={14} />}
      <span>{children}</span>
    </motion.button>
  );
}
