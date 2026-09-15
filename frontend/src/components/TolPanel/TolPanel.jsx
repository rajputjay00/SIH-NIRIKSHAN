import React, { useEffect, useMemo, useState } from 'react';
import { Scale, Layers, FileDown } from 'lucide-react';
import { Button } from '../Button/Button';
import { RuleCard } from '../RuleCard/RuleCard';
import { useT } from '../../i18n/useT';
import { weighPack, inspectLot, downloadLotForm } from '../../api';
import styles from './TolPanel.module.css';

const UNIT_OPTIONS = ['g', 'kg', 'ml', 'L', 'cm', 'm', 'N'];

function parseNumbers(text) {
  return String(text || '')
    .split(/[\s,;]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map(Number)
    .filter((n) => Number.isFinite(n));
}

function fmt(v, digits = 2) {
  if (v === null || v === undefined) return '—';
  const n = Number(v);
  return Number.isInteger(n) ? String(n) : n.toFixed(digits);
}

/**
 * Tol (तोल) — net quantity, MPE and lot inspection.
 * Reads the declared quantity from the scan (override allowed) and posts
 * officer-entered weights to /api/tol/*. Resulting findings (R31 / R32) are
 * handed back through onFinding so the Findings tab and summary update.
 */
export function TolPanel({ declaredField, onFinding }) {
  const { t } = useT();
  const [mode, setMode] = useState('single');

  const [declaredValue, setDeclaredValue] = useState('');
  const [declaredUnit, setDeclaredUnit] = useState('g');

  useEffect(() => {
    if (declaredField?.value != null) setDeclaredValue(String(declaredField.value));
    if (declaredField?.unit) setDeclaredUnit(declaredField.unit);
  }, [declaredField?.value, declaredField?.unit]);

  // single pack
  const [gross, setGross] = useState('');
  const [tare, setTare] = useState('');
  const [net, setNet] = useState('');
  const [resolution, setResolution] = useState('');
  const [single, setSingle] = useState(null);

  // lot
  const [lotSize, setLotSize] = useState('1000');
  const [lotTares, setLotTares] = useState('');
  const [lotSamples, setLotSamples] = useState('');
  const [lot, setLot] = useState(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const sampleCount = useMemo(() => parseNumbers(lotSamples).length, [lotSamples]);
  const requiredSamples = Number(lotSize) > 4000 ? 80 : 32;

  const declared = () => ({
    declared_value: Number(declaredValue),
    declared_unit: declaredUnit,
  });

  const canWeigh = Number(declaredValue) > 0 && (net !== '' || (gross !== '' && tare !== ''));

  const runSingle = async () => {
    setBusy(true); setError(null);
    try {
      const payload = { ...declared() };
      if (net !== '') payload.net = Number(net);
      if (gross !== '') payload.gross = Number(gross);
      if (tare !== '') payload.tare = Number(tare);
      if (resolution !== '') payload.resolution = Number(resolution);
      const res = await weighPack(payload);
      setSingle(res);
      onFinding?.(res.finding);
    } catch (e) {
      setError(e.message || 'Weighing check failed');
    } finally {
      setBusy(false);
    }
  };

  const lotPayload = () => ({
    ...declared(),
    lot_size: Number(lotSize),
    tares: parseNumbers(lotTares),
    samples: parseNumbers(lotSamples).map((g) => ({ gross: g })),
  });

  const runLot = async () => {
    setBusy(true); setError(null);
    try {
      const res = await inspectLot(lotPayload());
      setLot(res);
      onFinding?.(res.finding);
    } catch (e) {
      setError(e.message || 'Lot inspection failed');
    } finally {
      setBusy(false);
    }
  };

  const downloadForm = async () => {
    setBusy(true); setError(null);
    try {
      const blob = await downloadLotForm(lotPayload());
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      setError(e.message || 'Form generation failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.panel}>
      <div className={styles.modeRow}>
        <button type="button" className={`${styles.modeBtn} ${mode === 'single' ? styles.modeActive : ''}`} onClick={() => setMode('single')}>
          <Scale size={16} /> {t('tol_single_pack')}
        </button>
        <button type="button" className={`${styles.modeBtn} ${mode === 'lot' ? styles.modeActive : ''}`} onClick={() => setMode('lot')}>
          <Layers size={16} /> {t('tol_lot_mode')}
        </button>
      </div>

      <div className={styles.declaredRow}>
        <label className={styles.field}>
          <span>{t('tol_declared_qty')}</span>
          <div className={styles.inline}>
            <input type="number" inputMode="decimal" value={declaredValue} onChange={(e) => setDeclaredValue(e.target.value)} className={styles.input} />
            <select value={declaredUnit} onChange={(e) => setDeclaredUnit(e.target.value)} className={styles.select}>
              {UNIT_OPTIONS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </label>
        <div className={styles.hint}>{declaredField?.raw ? `${t('tol_from_label')}: "${declaredField.raw}"` : t('tol_declared_hint')}</div>
      </div>

      {mode === 'single' && (
        <div className={styles.grid}>
          <label className={styles.field}><span>{t('tol_gross')}</span>
            <input type="number" inputMode="decimal" value={gross} onChange={(e) => setGross(e.target.value)} className={styles.input} /></label>
          <label className={styles.field}><span>{t('tol_tare')}</span>
            <input type="number" inputMode="decimal" value={tare} onChange={(e) => setTare(e.target.value)} className={styles.input} /></label>
          <label className={styles.field}><span>{t('tol_net')}</span>
            <input type="number" inputMode="decimal" value={net} onChange={(e) => setNet(e.target.value)} className={styles.input} placeholder={t('tol_optional')} /></label>
          <label className={styles.field}><span>{t('tol_resolution')}</span>
            <input type="number" inputMode="decimal" value={resolution} onChange={(e) => setResolution(e.target.value)} className={styles.input} placeholder="0.1" /></label>
          <div className={styles.actions}>
            <Button onClick={runSingle} disabled={busy || !canWeigh} icon={Scale}>{t('tol_check_mpe')}</Button>
          </div>
        </div>
      )}

      {mode === 'single' && single && (
        <div className={styles.result}>
          <div className={styles.stats}>
            <Stat label={t('tol_measured_net')} value={`${fmt(single.net_base)} ${single.base_unit}`} />
            <Stat label={t('tol_error')} value={`${single.error_base > 0 ? '+' : ''}${fmt(single.error_base)} ${single.base_unit}`} tone={single.within_mpe ? 'pass' : 'fail'} />
            <Stat label={t('tol_mpe')} value={`${fmt(single.mpe_base)} ${single.base_unit} (${single.mpe_band})`} />
            {single.exceeds_2x_mpe && <Stat label={t('tol_aggravated')} value=">2×MPE" tone="fail" />}
          </div>
          <RuleCard finding={single.finding} />
        </div>
      )}

      {mode === 'lot' && (
        <div className={styles.grid}>
          <label className={styles.field}><span>{t('tol_lot_size')}</span>
            <input type="number" inputMode="numeric" value={lotSize} onChange={(e) => setLotSize(e.target.value)} className={styles.input} /></label>
          <label className={styles.field}><span>{t('tol_tares')}</span>
            <input type="text" value={lotTares} onChange={(e) => setLotTares(e.target.value)} className={styles.input} placeholder="4.0  or  4.0 4.1 4.0 4.2 4.1" /></label>
          <label className={`${styles.field} ${styles.wide}`}>
            <span>{t('tol_samples')} — {sampleCount}/{requiredSamples}</span>
            <textarea value={lotSamples} onChange={(e) => setLotSamples(e.target.value)} className={styles.textarea} rows={4}
              placeholder="504.2 505.0 503.8 …  (one gross weight per package, space or newline separated)" />
          </label>
          <div className={styles.actions}>
            <Button onClick={runLot} disabled={busy || sampleCount === 0 || !(Number(declaredValue) > 0)} icon={Layers}>{t('tol_run_lot')}</Button>
            <Button variant="secondary" onClick={downloadForm} disabled={busy || sampleCount === 0 || !(Number(declaredValue) > 0)} icon={FileDown}>
              {t('tol_download_form')} {lot?.form ? lot.form : ''}
            </Button>
          </div>
        </div>
      )}

      {mode === 'lot' && lot && (
        <div className={styles.result}>
          <div className={styles.stats}>
            <Stat label={t('tol_lot_status')} value={lot.status} tone={lot.status === 'APPROVED' ? 'pass' : lot.status === 'REJECTED' ? 'fail' : 'review'} />
            <Stat label={t('tol_sample')} value={`${lot.sample_size_weighed} / ${lot.sample_size_required}`} />
            <Stat label={t('tol_mean')} value={`${fmt(lot.mean)} ${lot.base_unit}`} />
            <Stat label={t('tol_corrected_avg')} value={`${fmt(lot.corrected_average)} ${lot.base_unit}`} tone={lot.corrected_average >= lot.criteria.corrected_average_min ? 'pass' : 'fail'} />
            <Stat label="T1 / T2" value={`${lot.t1_count} (≤${lot.criteria.allowed_t1}) / ${lot.t2_count} (≤${lot.criteria.allowed_t2})`} tone={lot.t1_count <= lot.criteria.allowed_t1 && lot.t2_count <= lot.criteria.allowed_t2 ? 'pass' : 'fail'} />
            <Stat label={t('tol_tare')} value={`${lot.tare.method}${lot.tare.tare != null ? ` · ${fmt(lot.tare.tare)} ${lot.base_unit}` : ''}`} tone={lot.tare.ok ? 'pass' : 'review'} />
          </div>
          {lot.reasons?.map((r, i) => <div key={i} className={styles.reason}>{r}</div>)}
          {lot.notes?.map((n, i) => <div key={i} className={styles.note}>{n}</div>)}
          <RuleCard finding={lot.finding} />
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}
      <div className={styles.footnote}>{t('tol_footnote')}</div>
    </div>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className={`${styles.stat} ${tone ? styles[`tone_${tone}`] : ''}`}>
      <div className={styles.statLabel}>{label}</div>
      <div className={styles.statValue}>{value}</div>
    </div>
  );
}
