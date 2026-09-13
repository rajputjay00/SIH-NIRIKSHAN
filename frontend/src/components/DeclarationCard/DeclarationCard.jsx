import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useT } from '../../i18n/useT';
import styles from './DeclarationCard.module.css';

export function DeclarationCard({ label, field, className = '' }) {
  const reducedMotion = useReducedMotion();
  const { t } = useT();

  const isFound = Boolean(field && (field.value !== null && field.value !== undefined || field.raw));
  const isCrimp = field?.source === 'crimp_notice' || field?.declared_elsewhere === 'crimp' || field?.source === 'crimp' || field?.surface === 'crimp';
  const confidence = field?.confidence ? Math.min(Math.max(field.confidence * 100, 0), 100) : 0;

  let displayValue = '-';
  if (isFound) {
    if (typeof field.value === 'object' && field.value !== null) {
      displayValue = field.value.name || field.value.phone || field.value.email || field.raw;
    } else {
      displayValue = String(field.value ?? field.raw);
    }
  }

  return (
    <div className={`${styles.declCard} ${className}`}>
      <div className={styles.titleRow}>
        <span className={styles.fieldTitle}>{label}</span>
        {isCrimp && <span className={styles.crimpChip}>{t('resolved_from_crimp')}</span>}
      </div>

      <div className={`${styles.fieldValue} ${!isFound ? styles.notFound : ''}`}>
        {isFound ? displayValue : t('not_applicable_header')}
      </div>

      {isFound && (
        <>
          <div className={styles.confTrack}>
            <motion.div
              className={styles.confFill}
              initial={reducedMotion ? { width: `${confidence}%` } : { width: '0%' }}
              animate={{ width: `${confidence}%` }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
          </div>

          {field.raw && <div className={styles.rawText}>{field.raw}</div>}
        </>
      )}
    </div>
  );
}
