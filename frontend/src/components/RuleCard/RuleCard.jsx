import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Eye, CheckSquare, Square, CheckCircle2 } from 'lucide-react';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useT } from '../../i18n/useT';
import { Button } from '../Button/Button';
import styles from './RuleCard.module.css';

export function RuleCard({
  finding,
  onShowOnImage,
  isExpanded: defaultExpanded = false,
  isConfirmed = false,
  onConfirmManual,
  className = ''
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [showTrail, setShowTrail] = useState(false);
  const reducedMotion = useReducedMotion();
  const { lang, t } = useT();

  const isHindi = lang === 'hi';
  const message = isHindi && finding.message_hi ? finding.message_hi : (finding.message_en || finding.message);
  const fixHint = finding.fix_hint_en || finding.fix_hint;

  const verdict = finding.verdict || 'N/A';
  const isManual = verdict === 'MANUAL';
  const isInfo = verdict === 'INFO';
  const isFromCrimp = finding.source === 'crimp' || finding.surface === 'crimp';

  let badgeClass = styles[`badge${verdict.replace('/', '').replace(' ', '_')}`] || styles.badgeNA;
  if (isManual && isConfirmed) {
    badgeClass = styles.badgeCONFIRMED;
  }

  const handleManualToggle = (e) => {
    e.stopPropagation();
    if (onConfirmManual) {
      onConfirmManual(finding.rule_id);
    }
  };

  return (
    <motion.div
      className={`${styles.ruleCard} ${isManual ? styles.manualCard : ''} ${className}`}
      layout={!reducedMotion}
      initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <div className={styles.headerRow} onClick={() => setExpanded(!expanded)}>
        <div className={styles.ruleMeta}>
          <span className={styles.rulePill}>{finding.rule_id}</span>
          <span className={styles.ruleRef}>{finding.rule_ref}</span>
          <span className={`${styles.verdictBadge} ${badgeClass}`}>
            {isManual ? (isConfirmed ? 'CONFIRMED' : 'MANUAL') : verdict}
          </span>
          {isFromCrimp && (
            <span className={styles.crimpChip}>{t('resolved_from_crimp')}</span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {finding.trail && finding.trail.length > 0 && (
            <button
              type="button"
              className={styles.whyBtn}
              onClick={(e) => {
                e.stopPropagation();
                setShowTrail(!showTrail);
                if (!expanded) setExpanded(true);
              }}
            >
              {t('why_trail_btn')}
            </button>
          )}
          {expanded ? <ChevronUp size={18} color="var(--grey-500)" /> : <ChevronDown size={18} color="var(--grey-500)" />}
        </div>
      </div>

      <div className={styles.message}>{message}</div>

      {/* MANUAL Verification Checkbox */}
      {isManual && (
        <div className={styles.manualCheckRow} onClick={handleManualToggle}>
          {isConfirmed ? (
            <CheckSquare size={20} color="var(--pass)" />
          ) : (
            <Square size={20} color="var(--grey-500)" />
          )}
          <span className={isConfirmed ? styles.confirmedText : styles.unconfirmedText}>
            {isConfirmed ? 'I have verified this (Confirmed by Officer)' : 'I have verified this (Officer confirmation required)'}
          </span>
        </div>
      )}

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

            {/* Why Trail Timeline */}
            {showTrail && finding.trail && (
              <div className={styles.trailContainer}>
                <div className={styles.trailHeader}>{t('trail_timeline')}</div>
                <div className={styles.trailTimeline}>
                  {finding.trail.map((item, idx) => {
                    const isFailStep = item.status === 'FAIL' || (item.detail && (item.detail.includes('-> False') || item.detail.includes('FAIL')));
                    const isReviewStep = item.status === 'NEEDS_REVIEW' || (item.detail && item.detail.includes('NEEDS_REVIEW'));

                    let stepClass = styles.stepPass;
                    let statusBadge = item.status || 'PASS';
                    if (isFailStep) {
                      stepClass = styles.stepFail;
                      statusBadge = item.status || 'FAIL';
                    } else if (isReviewStep) {
                      stepClass = styles.stepReview;
                      statusBadge = item.status || 'NEEDS_REVIEW';
                    }

                    const titleText = item.title || (item.step ? item.step.replace('_', ' ').toUpperCase() : `Step ${idx + 1}`);

                    return (
                      <div key={idx} className={`${styles.trailStep} ${stepClass}`}>
                        <div className={styles.stepDot} />
                        <div className={styles.stepContent}>
                          <div className={styles.stepTitle}>
                            <span>{titleText}</span>
                            <span className={styles.stepBadge}>{statusBadge}</span>
                          </div>
                          {item.input && <div className={styles.stepInput}>Input: "{item.input}"</div>}
                          {item.detail && <div className={styles.stepDetail}>{item.detail}</div>}
                        </div>
                      </div>
                    );
                  })}
                </div>
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

