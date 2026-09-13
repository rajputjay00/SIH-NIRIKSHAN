import React from 'react';
import styles from './EntityCard.module.css';

export function EntityCard({ entity, className = '' }) {
  if (!entity) return null;

  return (
    <div className={`${styles.entityCard} ${className}`}>
      <div className={styles.header}>
        <span className={styles.roleTag}>{entity.role || 'Manufacturer'}</span>
      </div>

      {entity.name && <div className={styles.name}>{entity.name}</div>}
      {entity.address && <div className={styles.address}>{entity.address}</div>}
      {entity.pin && <div className={styles.pin}>PIN: {entity.pin}</div>}
    </div>
  );
}
