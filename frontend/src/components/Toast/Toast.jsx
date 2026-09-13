import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './Toast.module.css';

export function Toast({ message, type = 'error', onClose, duration = 4000, className = '' }) {
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    if (!message || !onClose) return;
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          className={`${styles.toastContainer} ${styles[type]} ${className}`}
          initial={reducedMotion ? { opacity: 1, y: 0 } : { y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={reducedMotion ? { opacity: 0 } : { y: -20, opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <span className={styles.toastText}>{message}</span>
          {onClose && (
            <button type="button" className={styles.closeBtn} onClick={onClose}>
              <X size={16} />
            </button>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
