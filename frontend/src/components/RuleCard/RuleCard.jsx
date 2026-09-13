import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Eye } from 'lucide-react';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useT } from '../../i18n/useT';
import { Button } from '../Button/Button';
import styles from './RuleCard.module.css';

export function RuleCard({ finding, onShowOnImage, isExpanded: defaultExpanded = false, className = '' }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const reducedMotion = useReducedMotion();
  const { lang, t } = useT();

  const isHindi = lang === 'hi';
  const message = isHindi && finding.message_hi ? finding.message_hi : (finding.message_en || finding.message);
  const fixHint = finding.fix_hint_en || finding.fix_hint;

  const verdict = finding.verdict || 'N/A';
  const badgeClass = styles[`badge${verdict.replace('/', '').replace(' ', '_')}`] || styles.badgeNA;

  return (
    <motion.div
      className={`${styles.ruleCard} ${className}`}
      layout={!reducedMotion}
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className={styles.headerRow} onClick={() => setExpanded(!expanded)}>
        <div className={styles.ruleMeta}>
          <span className={styles.rulePill}>{finding.rule_id}</span>
          <span className={styles.ruleRef}>{finding.rule_ref}</span>
          <span className={`${styles.verdictBadge} ${badgeClass}`}>{verdict}</span>
        </div>
        <div>
          {expanded ? <ChevronUp size={18} color="var(--grey-500)" /> : <ChevronDown size={18} color="var(--grey-500)" />}
        </div>
      </div>

      <div className={styles.message}>{message}</div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            className={styles.detailsBody}
            initial={reducedMotion ? { opacity: 1 } : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={reducedMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            {finding.extracted !== undefined && finding.extracted !== null && (
              <div className={styles.detailItem}>
                <span className={styles.detailLabel}>{t('extracted_label')}:</span>
                <span className={styles.detailValue}>{String(finding.extracted)}</span>
              </div>
            )}

            {finding.expected && (
              <div className={styles.detailItem}>
                <span className={styles.detailLabel}>{t('expected_label')}:</span>
                <span className={styles.detailValue}>{finding.expected}</span>
              </div>
            )}

            {fixHint && (
              <div className={styles.fixHint}>
                <strong>{t('fix_hint_label')}:</strong> {fixHint}
              </div>
            )}

            {finding.evidence_bbox && onShowOnImage && (
              <div className={styles.actions}>
                <Button variant="secondary" icon={Eye} onClick={(e) => { e.stopPropagation(); onShowOnImage(finding.rule_id); }}>
                  {t('show_on_image')}
                </Button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
