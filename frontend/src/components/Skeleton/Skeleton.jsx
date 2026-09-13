import React from 'react';
import styles from './Skeleton.module.css';

export function Skeleton({ width = '100%', height = '20px', borderRadius, className = '', ...props }) {
  return (
    <div
      className={`${styles.skeleton} ${className}`}
      style={{ width, height, borderRadius }}
      {...props}
    />
  );
}
