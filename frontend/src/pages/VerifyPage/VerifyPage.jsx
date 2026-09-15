import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useT } from '../../i18n/useT';
import styles from './VerifyPage.module.css';

export function VerifyPage() {
  const { hash } = useParams();
  const { t } = useT();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!hash) {
      setError(t('verify_not_found'));
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    fetch(`/api/verify/${hash}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(t('verify_not_found'));
        }
        return res.json();
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || t('verify_not_found'));
        setLoading(false);
      });
  }, [hash, t]);

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>{t('verify_loading')}</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={styles.container}>
        <div className={styles.errorCard}>
          <div className={styles.errorTitle}>404 — {t('verify_not_found')}</div>
          <div className={styles.errorText}>
            {t('verify_image_hash')}: {hash}
          </div>
        </div>
      </div>
    );
  }

  const statusKey = data.status === 'COMPLIANT'
    ? 'verdict_compliant'
    : data.status === 'NON_COMPLIANT'
    ? 'verdict_non_compliant'
    : data.status === 'OFFICER_REVIEW_REQUIRED'
    ? 'verdict_review'
    : 'verdict_exempt';

  const verdictClass = data.status === 'COMPLIANT'
    ? styles.verdictPass
    : data.status === 'NON_COMPLIANT'
    ? styles.verdictFail
    : data.status === 'OFFICER_REVIEW_REQUIRED'
    ? styles.verdictReview
    : styles.verdictNa;

  const counts = data.counts || {};
  const findings = data.findings || [];

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>{t('verify_title')}</h1>
          <p className={styles.subtitle}>{t('verify_subtitle')}</p>
        </div>

        <div className={`${styles.verdictBanner} ${verdictClass}`}>
          <span>{t(statusKey) || data.status}</span>
          <span className={`${styles.chainBadge} ${data.chain_verified ? styles.chainVerified : styles.chainUnverified}`}>
            {data.chain_verified ? `✓ ${t('verify_chain_intact')}` : `⚠ ${t('verify_chain_broken')}`}
          </span>
        </div>

        <div className={styles.grid}>
          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>{t('verify_generated_at')}</span>
            <span className={styles.metaValue}>{data.generated_at || '—'}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>{t('verify_officer')}</span>
            <span className={styles.metaValue}>{data.officer_name || '—'}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>{t('verify_premises')}</span>
            <span className={styles.metaValue}>{data.premises || '—'}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>{t('verify_rules_version')}</span>
            <span className={styles.metaValue}>{data.rules_version || '—'}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>{t('verify_model_version')}</span>
            <span className={styles.metaValue}>{data.model_version || '—'}</span>
          </div>

          <div className={styles.metaItem}>
            <span className={styles.metaLabel}>{t('verify_image_hash')}</span>
            <span className={`${styles.metaValue} ${styles.monoValue}`}>{data.image_sha256}</span>
          </div>
        </div>

        {Object.keys(counts).length > 0 && (
          <div className={styles.countsRow}>
            {counts.pass !== undefined && (
              <div className={`${styles.countPill} ${styles.verdictPass}`}>
                {t('count_pass')}: {counts.pass}
              </div>
            )}
            {counts.fail !== undefined && (
              <div className={`${styles.countPill} ${styles.verdictFail}`}>
                {t('count_fail')}: {counts.fail}
              </div>
            )}
            {counts.review !== undefined && (
              <div className={`${styles.countPill} ${styles.verdictReview}`}>
                {t('count_review')}: {counts.review}
              </div>
            )}
            {counts.na !== undefined && (
              <div className={`${styles.countPill} ${styles.verdictNa}`}>
                {t('count_na')}: {counts.na}
              </div>
            )}
          </div>
        )}

        {findings.length > 0 && (
          <div className={styles.findingsSection}>
            <h2 className={styles.sectionTitle}>{t('verify_findings_header')}</h2>
            <table className={styles.findingsTable}>
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Verdict</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f, idx) => {
                  const fClass = f.verdict === 'PASS'
                    ? styles.verdictPass
                    : f.verdict === 'FAIL'
                    ? styles.verdictFail
                    : f.verdict === 'NEEDS_REVIEW'
                    ? styles.verdictReview
                    : styles.verdictNa;
                  return (
                    <tr key={idx}>
                      <td><strong>{f.rule_id}</strong></td>
                      <td>
                        <span className={`${styles.verdictChip} ${fClass}`}>
                          {f.verdict}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
