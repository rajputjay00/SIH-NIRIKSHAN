import React, { useState, useEffect } from 'react';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './CountChip.module.css';

export function CountChip({ label, count = 0, variant = 'pass', className = '' }) {
  const reducedMotion = useReducedMotion();
  const [displayCount, setDisplayCount] = useState(reducedMotion ? count : 0);

  useEffect(() => {
    if (reducedMotion) {
      setDisplayCount(count);
      return;
    }

    let start = 0;
    const end = parseInt(count, 10) || 0;
    if (start === end) {
      setDisplayCount(end);
      return;
    }

    const duration = 500;
    const startTime = performance.now();

    const updateCount = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const current = Math.floor(progress * (end - start) + start);
      setDisplayCount(current);
      if (progress < 1) {
        requestAnimationFrame(updateCount);
      } else {
        setDisplayCount(end);
      }
    };

    const animFrame = requestAnimationFrame(updateCount);
    return () => cancelAnimationFrame(animFrame);
  }, [count, reducedMotion]);

  return (
    <div className={`${styles.countChip} ${styles[variant.toLowerCase()]} ${className}`}>
      <span>{label}</span>
      <span className={styles.countBadge}>{displayCount}</span>
    </div>
  );
}
