import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './Drawer.module.css';

export function Drawer({ isOpen, onClose, title, children, className = '' }) {
  const reducedMotion = useReducedMotion();

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className={styles.backdrop}
          onClick={onClose}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className={`${styles.drawerPanel} ${className}`}
            onClick={(e) => e.stopPropagation()}
            initial={reducedMotion ? { opacity: 1, x: 0 } : { x: '100%' }}
            animate={{ x: 0 }}
            exit={reducedMotion ? { opacity: 0 } : { x: '100%' }}
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
          >
            <div className={styles.header}>
              <div className={styles.title}>{title}</div>
              <button type="button" className={styles.closeBtn} onClick={onClose}>
                <X size={20} />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
