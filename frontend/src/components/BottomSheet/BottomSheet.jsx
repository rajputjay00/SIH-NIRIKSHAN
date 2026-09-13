import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './BottomSheet.module.css';

export function BottomSheet({ isOpen, onClose, children, className = '' }) {
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
            className={`${styles.sheetContent} ${className}`}
            onClick={(e) => e.stopPropagation()}
            drag={reducedMotion ? false : 'y'}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.5 }}
            onDragEnd={(e, info) => {
              if (info.offset.y > 100) {
                onClose();
              }
            }}
            initial={reducedMotion ? { opacity: 1, y: 0 } : { y: '100%' }}
            animate={{ y: 0 }}
            exit={reducedMotion ? { opacity: 0 } : { y: '100%' }}
            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
          >
            <div className={styles.dragHandle} />
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
