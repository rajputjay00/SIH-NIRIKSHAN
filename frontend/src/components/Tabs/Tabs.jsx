import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './Tabs.module.css';

export function Tabs({ tabs = [], activeTab, onChange, className = '' }) {
  const reducedMotion = useReducedMotion();

  return (
    <div className={`${styles.tabsContainer} ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onChange(tab.id)}
            className={`${styles.tabItem} ${isActive ? styles.activeTab : ''}`}
          >
            <span>{tab.label}</span>
            {isActive && (
              <motion.div
                className={styles.activeUnderline}
                layoutId={reducedMotion ? undefined : 'activeUnderline'}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
