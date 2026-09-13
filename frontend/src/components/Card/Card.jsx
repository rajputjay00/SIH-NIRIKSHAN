import React from 'react';
import styles from './Card.module.css';

export function Card({ children, className = '', ...props }) {
  return (
    <div className={`${styles.card} ${className}`} {...props}>
      {children}
    </div>
  );
}

export function GlassCard({ children, className = '', ...props }) {
  return (
    <div className={`${styles.glassCard} ${className}`} {...props}>
      {children}
    </div>
  );
}
