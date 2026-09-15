import React, { useRef, useState } from 'react';
import { Link2, Upload, CheckCircle2, XCircle, Info } from 'lucide-react';
import { Button } from '../../components/Button/Button';
import { Card } from '../../components/Card/Card';
import { RuleCard } from '../../components/RuleCard/RuleCard';
import { Chip } from '../../components/Chip/Chip';
import { Skeleton } from '../../components/Skeleton/Skeleton';
import { useT } from '../../i18n/useT';
import { checkListing } from '../../api';
import styles from './ListingPage.module.css';

/**
 * Jaal — e-commerce listing check: Rule 6(10) mandatory declarations and
 * Rule 31 font parity. Page text can be fetched from a URL; a screenshot is
 * required before font sizes can be measured at all.
 */
export function ListingPage() {
  const { t } = useT();
  const [url, setUrl] = useState('');
  const [isImport, setIsImport] = useState(false);
  const [files, setFiles] = useState([]);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  const canSubmit = Boolean(url.trim()) || files.length > 0;

  const run = async () => {
    setBusy(true); setError(null);
    try {
      setResult(await checkListing({ url: url.trim() || undefined, files, isImport }));
    } catch (e) {
      setError(e.message || 'Listing check failed');
    } finally {
      setBusy(false);
    }
  };

  const presence = result?.listing?.presence;
  const parity = result?.listing?.font_parity;

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>{t('listing_title')}</h1>
      <p className={styles.subtitle}>{t('listing_subtitle')}</p>

      <Card className={styles.form}>
        <label className={styles.field}>
          <span>{t('listing_url_label')}</span>
          <div className={styles.inputRow}>
            <Link2 size={16} color="var(--grey-500)" />
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder={t('listing_url_placeholder')}
              className={styles.input}
            />
          </div>
        </label>

        <div className={styles.field}>
          <span>{t('listing_screenshots_label')}</span>
          <div className={styles.uploadRow}>
            <Button variant="secondary" icon={Upload} onClick={() => fileRef.current?.click()}>
              {files.length > 0 ? `${files.length}` : '+'}
            </Button>
            <span className={styles.hint}>{t('listing_screenshots_hint')}</span>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            hidden
            onChange={(e) => setFiles(Array.from(e.target.files || []).slice(0, 6))}
          />
        </div>

        <div className={styles.chipRow}>
          <Chip selected={isImport} onClick={() => setIsImport(!isImport)}>
            {t('imported_label')}
          </Chip>
        </div>

        <Button onClick={run} disabled={busy || !canSubmit}>
          {t('listing_check_btn')}
        </Button>
        {!canSubmit && <span className={styles.hint}>{t('listing_empty')}</span>}
        {error && <div className={styles.error}>{error}</div>}
      </Card>

      {busy && <Skeleton height="160px" />}

      {result && !busy && (
        <>
          <Card className={styles.block}>
            <div className={styles.blockHead}>
              <span>{t('listing_mode_label')}</span>
              <span className={styles.mono}>{result.mode}</span>
            </div>

            {presence?.present?.length > 0 && (
              <>
                <div className={styles.listLabel}>{t('listing_present')}</div>
                <ul className={styles.list}>
                  {presence.present.map((p) => (
                    <li key={p.field} className={styles.itemOk}>
                      <CheckCircle2 size={14} /> {p.label}
                    </li>
                  ))}
                </ul>
              </>
            )}

            {presence?.missing?.length > 0 && (
              <>
                <div className={styles.listLabel}>{t('listing_missing')}</div>
                <ul className={styles.list}>
                  {presence.missing.map((m) => (
                    <li key={m.field} className={styles.itemBad}>
                      <XCircle size={14} /> {m.label}
                    </li>
                  ))}
                </ul>
              </>
            )}

            {presence?.optional?.length > 0 && (
              <>
                <div className={styles.listLabel}>{t('listing_optional')}</div>
                <ul className={styles.list}>
                  {presence.optional.map((o) => (
                    <li key={o.field} className={styles.itemInfo}>
                      <Info size={14} /> {o.label}
                    </li>
                  ))}
                </ul>
              </>
            )}

            {parity && (
              <div className={styles.parityRow}>
                <span>{t('listing_font_parity')}</span>
                <span className={`${styles.mono} ${parity.ok ? styles.ok : styles.warn}`}>
                  {parity.net_quantity_height_px} px / {parity.mrp_height_px} px = {parity.ratio}
                </span>
              </div>
            )}
          </Card>

          <div className={styles.findings}>
            {(result.findings || [])
              .filter((f) => f.verdict !== 'N/A')
              .map((f) => <RuleCard key={f.rule_id} finding={f} />)}
          </div>
        </>
      )}
    </div>
  );
}
