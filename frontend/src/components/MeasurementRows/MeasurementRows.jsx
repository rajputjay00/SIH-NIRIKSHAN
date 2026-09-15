import React from 'react';
import { useT } from '../../i18n/useT';
import styles from './MeasurementRows.module.css';

const DIRECTIONS = ['above', 'below', 'left', 'right'];

function tone(ok) {
  return ok ? styles.ok : styles.warn;
}

/**
 * Maap — the measurements behind R19 (Rule 7(3)), R20 (Rule 8(1)) and R22 (Rule 9(1)(b)).
 * Estimated from OCR boxes and pixels, so every block says so: these numbers ask the officer
 * to confirm with a graduated scale, they never assert a violation on their own.
 */
export function MeasurementRows({ geometry, contrast }) {
  const { t } = useT();
  const clearSpace = geometry?.clear_space;
  const aspect = geometry?.aspect;
  const hasAny = clearSpace || aspect || contrast;
  if (!hasAny) return null;

  return (
    <div className={styles.wrap}>
      {clearSpace && (
        <div className={styles.block}>
          <div className={styles.blockHead}>
            <span>{t('maap_clear_space')}</span>
            <span className={styles.ruleRef}>{t('maap_rule')} 8(1)</span>
          </div>
          <div className={styles.rows}>
            {DIRECTIONS.map((d) => {
              const g = clearSpace.gaps?.[d];
              if (!g) return null;
              const isWorst = clearSpace.worst_direction === d;
              return (
                <div key={d} className={`${styles.row} ${isWorst ? styles.worst : ''}`}>
                  <span className={styles.dir}>{t(`maap_dir_${d}`)}</span>
                  {g.ratio === null || g.ratio === undefined ? (
                    <span className={`${styles.value} ${styles.ok}`}>{t('maap_clear')}</span>
                  ) : (
                    <>
                      <span className={`${styles.value} ${tone(g.ok)}`}>{g.ratio}×</span>
                      <span className={styles.required}>{t('maap_need')} {g.required}×</span>
                    </>
                  )}
                </div>
              );
            })}
          </div>
          <div className={styles.note}>
            {t('maap_numeral_height')}: <span className={styles.mono}>{clearSpace.numeral_height_px} px</span> · {t('maap_estimated')}
          </div>
        </div>
      )}

      {aspect && (
        <div className={styles.block}>
          <div className={styles.blockHead}>
            <span>{t('maap_aspect')}</span>
            <span className={styles.ruleRef}>{t('maap_rule')} 7(3)</span>
          </div>
          <div className={styles.rows}>
            <div className={styles.row}>
              <span className={styles.dir}>{t('maap_width_height')}</span>
              <span className={`${styles.value} ${tone(aspect.ok)}`}>{aspect.ratio}</span>
              <span className={styles.required}>{t('maap_need')} {aspect.min_ratio}</span>
            </div>
          </div>
          <div className={styles.note}>{t('maap_estimated')}</div>
        </div>
      )}

      {contrast && (
        <div className={styles.block}>
          <div className={styles.blockHead}>
            <span>{t('maap_contrast')}</span>
            <span className={styles.ruleRef}>{t('maap_rule')} 9(1)(b)</span>
          </div>
          <div className={styles.rows}>
            <div className={styles.row}>
              <span className={styles.dir}>{t('maap_luminance')}</span>
              <span className={`${styles.value} ${tone(contrast.ok)}`}>{contrast.ratio}:1</span>
              <span className={styles.required}>{t('maap_need')} {contrast.min_ratio ?? 3}:1</span>
            </div>
          </div>
          <div className={styles.note}>{t('maap_estimated')}</div>
        </div>
      )}
    </div>
  );
}
