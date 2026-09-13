import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useT } from '../../i18n/useT';
import styles from './VerdictBanner.module.css';

export function VerdictBanner({
  status = 'Compliant',
  exemptReason = null,
  isWholesale = false,
  children,
  className = ''
}) {
  const reducedMotion = useReducedMotion();
  const { t } = useT();

  const isCompliant = status === 'Compliant' || status.includes('Compliant');
  const isNonCompliant = status === 'Non-compliant';
  const isReview = (status.includes('Officer') || status.includes('Review')) && !status.includes('after officer confirmation');
  const isExempt = status === 'Exempt';

  let bannerClass = styles.compliant;
  let translatedStatus = status.includes('after officer confirmation')
    ? 'Compliant (after officer confirmation)'
    : t('verdict_compliant');

  if (isNonCompliant) {
    bannerClass = styles.nonCompliant;
    translatedStatus = t('verdict_non_compliant');
  } else if (isReview) {
    bannerClass = styles.reviewRequired;
    translatedStatus = t('verdict_review');
  } else if (isExempt) {
    bannerClass = styles.exempt;
    translatedStatus = t('verdict_exempt');
  }

  // Stamp effect for compliant
  const containerVariants = {
    initial: isCompliant && !reducedMotion ? { scale: 1.12, rotate: -2, opacity: 0 } : { scale: 1, opacity: 0 },
    animate: { scale: 1, rotate: 0, opacity: 1 },
  };

  return (
    <motion.div
      className={`${styles.bannerContainer} ${bannerClass} ${className}`}
      variants={containerVariants}
      initial="initial"
      animate="animate"
      transition={{ type: 'spring', stiffness: 260, damping: 18 }}
    >
      <div>
        <div className={styles.statusText}>{translatedStatus}</div>
        {exemptReason && <div className={styles.exemptReason}>{exemptReason}</div>}
        {isWholesale && <div className={styles.exemptReason}>Wholesale package — Rule 24 applies</div>}
      </div>

      {children}

      {/* Ripple ring for Compliant */}
      {isCompliant && !reducedMotion && (
        <motion.div
          className={styles.rippleRing}
          initial={{ scale: 0.5, opacity: 0.8 }}
          animate={{ scale: 2.2, opacity: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      )}
    </motion.div>
  );
}
