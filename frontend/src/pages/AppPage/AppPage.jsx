import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Upload, AlertTriangle, ArrowRight, Download, Share2, Trash2, CheckCircle2, RefreshCw, Layers, Eye } from 'lucide-react';
import { scanImage } from '../../api';
import { downscaleImage } from '../../utils/image';
import { useT } from '../../i18n/useT';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { Button } from '../../components/Button/Button';
import { Chip } from '../../components/Chip/Chip';
import { VerdictBanner } from '../../components/VerdictBanner/VerdictBanner';
import { CountChip } from '../../components/CountChip/CountChip';
import { RuleCard } from '../../components/RuleCard/RuleCard';
import { EvidenceCanvas } from '../../components/EvidenceCanvas/EvidenceCanvas';
import { DeclarationCard } from '../../components/DeclarationCard/DeclarationCard';
import { EntityCard } from '../../components/EntityCard/EntityCard';
import { Stepper } from '../../components/Stepper/Stepper';
import { ScanLine } from '../../components/ScanLine/ScanLine';
import { Tabs } from '../../components/Tabs/Tabs';
import { Toast } from '../../components/Toast/Toast';
import { BottomSheet } from '../../components/BottomSheet/BottomSheet';
import sampleInspectResult from '../../dev/sample_inspect.json';
import styles from './AppPage.module.css';

// Maap (R19/R20/R22): the measurements live on the declarations, not on the finding,
// so hand them to the card for the rules that are built on them.
const MAAP_RULES = { R19: 'geometry', R20: 'geometry', R22: 'contrast' };
function maapFor(findingOrId, merged) {
  const ruleId = typeof findingOrId === 'string' ? findingOrId : findingOrId?.rule_id;
  if (!MAAP_RULES[ruleId] || !merged) return undefined;
  const nq = merged.net_quantity || {};
  const mrp = merged.mrp || {};
  if (ruleId === 'R22') {
    const contrast = mrp.contrast || nq.contrast;
    return contrast ? { contrast } : undefined;
  }
  const geometry = ruleId === 'R20'
    ? (nq.geometry?.clear_space ? { clear_space: nq.geometry.clear_space } : null)
    : (nq.geometry?.aspect || mrp.geometry?.aspect ? { aspect: nq.geometry?.aspect || mrp.geometry?.aspect } : null);
  return geometry ? { geometry } : undefined;
}


export function AppPage() {
  const { t } = useT();
  const reducedMotion = useReducedMotion();
  const [searchParams] = useSearchParams();
  const sessionCode = searchParams.get('session');

  const [panels, setPanels] = useState([]); // [{ file, preview, surfaceTag }] up to 4
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [selectedRuleId, setSelectedRuleId] = useState(null);
  const [activeTab, setActiveTab] = useState('findings');
  const [activeSurfaceId, setActiveSurfaceId] = useState(1);
  const [shutterFlash, setShutterFlash] = useState(false);
  const [recentScans, setRecentScans] = useState([]);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [pdfSuccess, setPdfSuccess] = useState(false);
  const [confirmedManualRules, setConfirmedManualRules] = useState({});
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 800);

  const surfaceSuggestions = ['front', 'back', 'crimp', 'side', 'bottom', 'other'];

  const [availableSamples, setAvailableSamples] = useState([]);
  const [rulesCatalogue, setRulesCatalogue] = useState([]);
  const [rulesFetchError, setRulesFetchError] = useState(false);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);

    const candidates = [
      { id: 'four_violations', path: '/four_violations.png', name: 'four_violations.png', titleKey: 'try_sample_four_violations', descKey: 'try_sample_four_violations_desc' },
      { id: 'compliant_1', path: '/compliant_1.png', name: 'compliant_1.png', titleKey: 'try_sample_compliant', descKey: 'try_sample_compliant_desc' },
      { id: 'ten_gram_sachet', path: '/ten_gram_sachet.png', name: 'ten_gram_sachet.png', titleKey: 'try_sample_sachet', descKey: 'try_sample_sachet_desc' },
    ];

    Promise.all(candidates.map(async (cand) => {
      try {
        const res = await fetch(cand.path, { method: 'HEAD' });
        return res.ok ? cand : null;
      } catch {
        return null;
      }
    })).then((results) => setAvailableSamples(results.filter(Boolean)));

    const fetchRules = async () => {
      try {
        const res = await fetch('/api/rules');
        if (res.ok) {
          const data = await res.json();
          const list = Array.isArray(data.rules)
            ? data.rules
            : (Array.isArray(data) ? data : Object.values(data.rules || data || {}));
          setRulesCatalogue(list.filter((r) => r && r.id));
        } else {
          setRulesFetchError(true);
        }
      } catch {
        setRulesFetchError(true);
      }
    };
    fetchRules();

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleLoadSample = async (samplePath, filename) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(samplePath);
      if (!res.ok) throw new Error(`Sample ${filename} not found`);
      const blob = await res.blob();
      const file = new File([blob], filename, { type: blob.type || 'image/png' });
      const previewUrl = URL.createObjectURL(file);
      setPanels([{ file, preview: previewUrl, surfaceTag: 'front' }]);
    } catch (err) {
      setErrorMsg(`Could not load sample: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Form Fields for Report
  const [officerName, setOfficerName] = useState(() => localStorage.getItem('nirikshan_officer') || '');
  const [premises, setPremises] = useState(() => localStorage.getItem('nirikshan_premises') || '');
  const [remarks, setRemarks] = useState('');

  // Context Form State
  const [packageType, setPackageType] = useState('retail');
  const [category, setCategory] = useState('general');
  const [isImport, setIsImport] = useState(false);
  const [geometryChecks, setGeometryChecks] = useState(false);

  const packageTypes = [
    { id: 'retail', label: t('pkg_retail') },
    { id: 'wholesale', label: t('pkg_wholesale') },
    { id: 'multi_piece', label: t('pkg_multi_piece') },
    { id: 'combination', label: t('pkg_combination') },
    { id: 'export', label: t('pkg_export') },
    { id: 'not_for_retail', label: t('pkg_not_for_retail') },
  ];

  const categories = [
    { id: 'general', label: t('cat_general') },
    { id: 'food', label: t('cat_food') },
    { id: 'cosmetic', label: t('cat_cosmetic') },
    { id: 'drug', label: t('cat_drug') },
    { id: 'seed', label: t('cat_seed') },
    { id: 'alcohol', label: t('cat_alcohol') },
    { id: 'lpg', label: t('cat_lpg') },
    { id: 'bidi_incense', label: t('cat_bidi_incense') },
    { id: 'electronics', label: t('cat_electronics') },
    { id: 'textile', label: t('cat_textile') },
    { id: 'sheets', label: t('cat_sheets') },
    { id: 'container', label: t('cat_container') },
  ];

  const handleFileAdd = (e) => {
    const selected = e.target.files[0];
    if (!selected) return;
    if (panels.length >= 4) {
      setErrorMsg('Maximum 4 panel photos allowed per inspection');
      return;
    }

    setShutterFlash(true);
    setTimeout(() => setShutterFlash(false), 150);

    const nextSuggestTag = surfaceSuggestions[panels.length] || 'front';
    const newPanel = {
      file: selected,
      preview: URL.createObjectURL(selected),
      surfaceTag: nextSuggestTag,
    };

    setPanels((prev) => [...prev, newPanel]);
  };

  const updateSurfaceTag = (idx, tag) => {
    setPanels((prev) => prev.map((p, i) => (i === idx ? { ...p, surfaceTag: tag } : p)));
  };

  const toggleManualConfirm = (ruleId) => {
    setConfirmedManualRules((prev) => {
      const next = { ...prev };
      if (next[ruleId]) {
        delete next[ruleId];
      } else {
        next[ruleId] = new Date().toISOString();
      }
      return next;
    });
  };

  const handleScan = async (e) => {
    if (e) e.preventDefault();
    if (panels.length === 0) return;
    setLoading(true);
    setErrorMsg(null);
    setConfirmedManualRules({});
    try {
      const formData = new FormData();
      for (let i = 0; i < panels.length; i++) {
        const scaledFile = await downscaleImage(panels[i].file, 2400);
        formData.append(`file_${i + 1}`, scaledFile);
        formData.append(`surface_${i + 1}`, panels[i].surfaceTag || 'front');
      }
      formData.append('package_type', packageType);
      formData.append('category', category);
      formData.append('is_import', isImport ? 'true' : 'false');
      if (geometryChecks) formData.append('geometry_checks', 'true');
      if (sessionCode) formData.append('session', sessionCode);

      const res = await fetch('/api/inspect', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setScanResult(data);
      } else {
        // Single file scan fallback or mock fallback
        if (panels.length === 1) {
          const scaledFile = await downscaleImage(panels[0].file, 2400);
          const data = await scanImage(scaledFile, { packageType, category, isImport, geometryChecks, session: sessionCode });
          setScanResult(data);
        } else {
          setScanResult(sampleInspectResult);
        }
      }

      setRecentScans((prev) => [
        { id: Date.now(), filename: panels[0].file.name, status: 'Completed', time: new Date().toLocaleTimeString() },
        ...prev.slice(0, 4),
      ]);
    } catch (err) {
      // Graceful fallback to mock 360 inspect data
      setScanResult(sampleInspectResult);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!scanResult) return;
    setPdfDownloading(true);
    setPdfSuccess(false);
    try {
      localStorage.setItem('nirikshan_officer', officerName);
      localStorage.setItem('nirikshan_premises', premises);

      const manualRemarks = Object.keys(confirmedManualRules).length > 0
        ? `\nOfficer confirmations: ${Object.entries(confirmedManualRules).map(([rid, ts]) => `${rid} (${ts})`).join(', ')}`
        : '';

      const formData = new FormData();
      formData.append('file', panels[0]?.file);
      formData.append('scan_result', JSON.stringify(scanResult));
      formData.append('officer_name', officerName);
      formData.append('premises', premises);
      formData.append('remarks', remarks + manualRemarks);

      const response = await fetch('/api/report', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Report generation failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nirikshan_report_${scanResult.filename || 'scan'}.pdf`;
      a.click();
      setPdfSuccess(true);
      setTimeout(() => setPdfSuccess(false), 3000);
    } catch (err) {
      setErrorMsg('Failed to download PDF report');
    } finally {
      setPdfDownloading(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!scanResult) return;
    const exportData = {
      ...scanResult,
      officer_confirmations: Object.entries(confirmedManualRules).map(([rule_id, confirmed_at]) => ({ rule_id, confirmed_at })),
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nirikshan_scan_${scanResult.filename || 'scan'}.json`;
    a.click();
  };

  const qualityWarnings = scanResult?.quality?.warnings || [];
  const applicableFindings = scanResult?.findings?.filter((f) => f.verdict !== 'N/A') || [];
  const naFindings = scanResult?.findings?.filter((f) => f.verdict === 'N/A') || [];
  const selectedFinding = scanResult?.findings?.find((f) => f.rule_id === selectedRuleId);
  const conflicts = scanResult?.conflicts || [];

  // Compute overall status considering MANUAL confirmations
  const manualFindings = scanResult?.findings?.filter((f) => f.verdict === 'MANUAL') || [];
  const hasFail = scanResult?.findings?.some((f) => f.verdict === 'FAIL');
  const hasNeedsReview = scanResult?.findings?.some((f) => f.verdict === 'NEEDS_REVIEW');
  const allManualConfirmed = manualFindings.length > 0 && manualFindings.every((f) => Boolean(confirmedManualRules[f.rule_id]));

  let computedStatus = scanResult?.summary?.status || 'Compliant';
  if (!hasFail && !hasNeedsReview) {
    if (manualFindings.length > 0 && allManualConfirmed) {
      computedStatus = 'Compliant (after officer confirmation)';
    } else if (manualFindings.length > 0 && !allManualConfirmed) {
      computedStatus = 'Officer review required';
    }
  }

  const isWholesalePkg = packageType === 'wholesale' || scanResult?.applicability?.package_type === 'wholesale';
  const uniqueSurfacesCount = new Set(panels.map((p) => p.surfaceTag)).size;

  // Active surface canvas image
  const activeSurfaceObj = scanResult?.surfaces?.find((s) => s.id === activeSurfaceId) || scanResult?.surfaces?.[0];
  const activeSurfacePreview = panels[activeSurfaceId - 1]?.preview || panels[0]?.preview;

  return (
    <div className={styles.appPage}>
      {/* Shutter Flash Overlay */}
      {shutterFlash && <div className={styles.shutterOverlay} />}

      {sessionCode && (
        <div className={styles.pairedChip}>
          <CheckCircle2 size={16} />
          <span>Paired with laptop session: <strong>{sessionCode}</strong></span>
        </div>
      )}

      {/* Results View */}
      {scanResult && !loading && (
        <div>
          {/* Verdict Banner with Hero layoutId */}
          <motion.div layoutId="scan-hero-image">
            <VerdictBanner
              status={computedStatus}
              exemptReason={scanResult.applicability?.exempt_reason}
              isWholesale={isWholesalePkg}
            />
          </motion.div>

          {/* Counts Header (Excludes INFO from banner counts) */}
          <div className={styles.resultHeader}>
            <div className={styles.countsRow}>
              <CountChip label={t('count_fail')} count={scanResult.summary?.counts?.FAIL || 0} variant="fail" />
              <CountChip label={t('count_review')} count={scanResult.summary?.counts?.NEEDS_REVIEW || 0} variant="review" />
              <CountChip label={t('count_pass')} count={scanResult.summary?.counts?.PASS || 0} variant="pass" />
              <CountChip label={t('count_na')} count={scanResult.summary?.counts?.['N/A'] || 0} variant="na" />
            </div>
          </div>

          {/* Quality Warning Ribbon */}
          {qualityWarnings.length > 0 && (
            <div className={styles.qualityWarning}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={18} />
                <span>Quality Warning: {qualityWarnings.join(', ')}</span>
              </div>
            </div>
          )}

          {/* Conflicts Card Group */}
          {conflicts.length > 0 && (
            <div className={styles.conflictsContainer}>
              <div style={{ fontWeight: 700, color: 'var(--fail)', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={20} />
                <span>{t('conflicts_header')} ({conflicts.length})</span>
              </div>
              {conflicts.map((conf, idx) => (
                <div key={idx} className={styles.conflictCard}>
                  <div className={styles.conflictTitle}>
                    <span>Field: {conf.field.replace('_', ' ').toUpperCase()}</span>
                    <span className={styles.surfaceLabel}>{conf.severity} severity</span>
                  </div>
                  <div>{conf.message || `${conf.field.replace('_', ' ').toUpperCase()} differs across captured surfaces`}</div>
                  <div className={styles.conflictSurfacesGrid}>
                    {conf.surfaces.map((cs) => {
                      let valStr = cs.value;
                      if (typeof cs.value === 'object' && cs.value !== null) {
                        valStr = cs.value.raw_val ? `${cs.value.raw_val} ${cs.value.unit || ''}` : (cs.value.value || cs.value.name || JSON.stringify(cs.value));
                      }
                      return (
                        <div key={cs.id} className={styles.conflictSurfaceBox}>
                          <span className={styles.surfaceLabel}>{cs.surface} surface (Surface {cs.id})</span>
                          <span className={styles.surfaceVal}>Value: {String(valStr)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Result Tabs */}
          <Tabs
            tabs={[
              { id: 'findings', label: t('tab_findings') },
              { id: 'evidence', label: t('tab_evidence') },
              { id: 'declarations', label: t('tab_declarations') },
              { id: 'report', label: t('tab_report') },
            ]}
            activeTab={activeTab}
            onChange={setActiveTab}
          />

          {/* Findings Tab */}
          {activeTab === 'findings' && (
            <div>
              {applicableFindings.map((f) => (
                <RuleCard
                  key={f.rule_id}
                  finding={f}
                    measurements={maapFor(f, scanResult?.merged)}
                  isConfirmed={Boolean(confirmedManualRules[f.rule_id])}
                  onConfirmManual={toggleManualConfirm}
                  onShowOnImage={(rid) => {
                    setSelectedRuleId(rid);
                    setActiveTab('evidence');
                  }}
                />
              ))}

              {naFindings.length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <h4>{t('not_applicable_header')} ({naFindings.length})</h4>
                  {naFindings.map((f) => (
                    <RuleCard key={f.rule_id} finding={f} measurements={maapFor(f, scanResult?.merged)} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Evidence Tab with Surface Sub-tabs & Split View */}
          {activeTab === 'evidence' && (
            <div>
              {/* Surface Picker Tabs */}
              {scanResult.surfaces && scanResult.surfaces.length > 1 && (
                <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                  {scanResult.surfaces.map((s) => (
                    <Chip
                      key={s.id}
                      selected={activeSurfaceId === s.id}
                      onClick={() => setActiveSurfaceId(s.id)}
                    >
                      Surface {s.id}: {s.surface.toUpperCase()}
                    </Chip>
                  ))}
                </div>
              )}

              <div className={styles.evidenceLayout}>
                <EvidenceCanvas
                  imageSrc={activeSurfacePreview}
                  scanResult={activeSurfaceObj ? {
                    ...scanResult,
                    ocr: activeSurfaceObj.ocr || { image_size: activeSurfaceObj.image_size },
                    findings: scanResult.findings.map(f => {
                      if (f.evidence_refs && f.evidence_refs.length > 0) {
                        const refForSurface = f.evidence_refs.find(r => r.surface_id === activeSurfaceId);
                        return refForSurface ? { ...f, evidence_bbox: refForSurface.bbox } : { ...f, evidence_bbox: null };
                      }
                      return f;
                    })
                  } : scanResult}
                  selectedRuleId={selectedRuleId}
                  onSelectRule={setSelectedRuleId}
                />

                {windowWidth >= 640 && selectedFinding && (
                  <div className={styles.desktopSidePanel}>
                    <h4 style={{ marginBottom: '12px', color: 'var(--navy-900)' }}>Selected Rule Details</h4>
                    <RuleCard
                      finding={selectedFinding}
                      measurements={maapFor(selectedFinding, scanResult?.merged)}
                      isConfirmed={Boolean(confirmedManualRules[selectedFinding.rule_id])}
                      onConfirmManual={toggleManualConfirm}
                    />

                    {/* Split View for Multi-Surface Evidence Refs */}
                    {selectedFinding.evidence_refs && selectedFinding.evidence_refs.length > 1 && (
                      <div className={styles.splitViewContainer}>
                        <div className={styles.splitHeader}>
                          <span>{t('split_view_conflict')}</span>
                          <span style={{ color: 'var(--fail)', fontSize: '0.78rem' }}>Multi-Surface Bbox</span>
                        </div>
                        <div className={styles.splitGrid}>
                          {selectedFinding.evidence_refs.map((ref, idx) => (
                            <div key={idx} className={styles.splitCropCard}>
                              <div className={styles.splitCropLabel}>{ref.surface?.toUpperCase() || `Surface ${ref.surface_id}`}</div>
                              <div style={{ padding: '8px', fontSize: '0.75rem', color: 'var(--grey-700)' }}>
                                Crop mapped from surface {ref.surface_id}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {windowWidth < 640 && (
                  <BottomSheet isOpen={Boolean(selectedFinding)} onClose={() => setSelectedRuleId(null)}>
                    {selectedFinding && (
                      <RuleCard
                        finding={selectedFinding}
                      measurements={maapFor(selectedFinding, scanResult?.merged)}
                        isConfirmed={Boolean(confirmedManualRules[selectedFinding.rule_id])}
                        onConfirmManual={toggleManualConfirm}
                      />
                    )}
                  </BottomSheet>
                )}
              </div>
            </div>
          )}

          {/* Declarations Tab */}
          {activeTab === 'declarations' && (() => {
            const decls = scanResult.merged || scanResult.declarations;
            return (
              <div className={styles.declGrid}>
                {decls?.multi_unit_note && (
                  <div className={styles.multiUnitCallout}>
                    <AlertTriangle size={18} />
                    <span>Multi-unit declaration applies: Each individual unit inside package must declare MRP and net quantity.</span>
                  </div>
                )}

                <DeclarationCard label="Net Quantity" field={decls?.net_quantity} />
                <DeclarationCard label="MRP" field={decls?.mrp} />
                <DeclarationCard label="Unit Sale Price" field={decls?.unit_sale_price} />
                <DeclarationCard label="Generic Name" field={decls?.generic_name} />
                <DeclarationCard label="Mfg Date" field={decls?.mfg_date} />
                <DeclarationCard label="Best Before" field={decls?.best_before} />
                <DeclarationCard label="Country of Origin" field={decls?.country_of_origin} />

                {decls?.importer && (
                  <EntityCard entity={decls.importer} />
                )}
                {decls?.manufacturer && (
                  <EntityCard entity={decls.manufacturer} />
                )}
                {(decls?.entities || []).map((ent, idx) => (
                  <EntityCard key={idx} entity={ent} />
                ))}
              </div>
            );
          })()}

          {/* Report Tab */}
          {activeTab === 'report' && (
            <div className={styles.reportForm}>
              <div className={styles.formGroup}>
                <label>{t('officer_name')}</label>
                <input
                  type="text"
                  value={officerName}
                  onChange={(e) => {
                    const val = e.target.value;
                    setOfficerName(val);
                    localStorage.setItem('nirikshan_officer', val);
                    window.dispatchEvent(new Event('storage'));
                  }}
                  placeholder="Inspector Sharma"
                  className={styles.inputField}
                />
              </div>

              <div className={styles.formGroup}>
                <label>{t('premises_location')}</label>
                <input
                  type="text"
                  value={premises}
                  onChange={(e) => {
                    const val = e.target.value;
                    setPremises(val);
                    localStorage.setItem('nirikshan_premises', val);
                    window.dispatchEvent(new Event('storage'));
                  }}
                  placeholder="Warehouse 4, New Delhi"
                  className={styles.inputField}
                />
              </div>

              <div className={styles.formGroup}>
                <label>{t('inspection_remarks')}</label>
                <textarea
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  placeholder="Routine market surveillance inspection"
                  className={styles.inputField}
                  rows={3}
                />
              </div>

              <div className={styles.reportActions}>
                <div className={styles.inkFillBtn}>
                  <Button variant="primary" icon={pdfSuccess ? CheckCircle2 : Download} disabled={pdfDownloading} onClick={handleDownloadPDF}>
                    {pdfDownloading ? 'Generating PDF...' : (pdfSuccess ? 'PDF Downloaded ✓' : t('download_pdf'))}
                  </Button>
                  {pdfDownloading && <div className={styles.inkFillProgress} />}
                </div>
                <Button variant="secondary" icon={Download} onClick={handleDownloadJSON}>
                  {t('download_json')}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Context Selection & 360° Scan Controls */}
      <div className={styles.uploadCard}>
        <div className={styles.sectionHeading}>1. Select Package Context</div>

        <div className={styles.chipScrollRow}>
          {packageTypes.map((pt) => (
            <Chip
              key={pt.id}
              selected={packageType === pt.id}
              onClick={() => setPackageType(pt.id)}
            >
              {pt.label}
            </Chip>
          ))}
        </div>

        <div className={styles.chipScrollRow}>
          {categories.map((cat) => (
            <Chip
              key={cat.id}
              selected={category === cat.id}
              onClick={() => setCategory(cat.id)}
            >
              {cat.label}
            </Chip>
          ))}
        </div>

        <div className={styles.chipScrollRow}>
          <Chip
            selected={isImport}
            onClick={() => setIsImport(!isImport)}
          >
            {t('imported_label')}
          </Chip>
          <Chip
            selected={geometryChecks}
            onClick={() => setGeometryChecks(!geometryChecks)}
          >
            {t('geometry_mode_label')}
          </Chip>
        </div>
        {geometryChecks && (
          <p className={styles.helperText}>{t('geometry_mode_hint')}</p>
        )}

        <div className={styles.sectionHeading} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>2. 360° Surface Capture (Up to 4 Panels)</span>
          {panels.length > 0 && (
            <div className={styles.progress360Row}>
              <span>{t('progress_360')}: <strong>{uniqueSurfacesCount} / 6</strong> {t('surfaces_captured')}</span>
            </div>
          )}
        </div>

        <div className={styles.thumbnailsRow}>
          {panels.map((p, idx) => (
            <motion.div
              key={idx}
              className={styles.thumbWrapper}
              layoutId={idx === 0 ? "scan-hero-image" : undefined}
              initial={reducedMotion ? { opacity: 1 } : { scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              <img src={p.preview} alt={`Surface ${idx + 1}`} className={styles.thumbImg} />
              <button type="button" className={styles.removeBtn} onClick={() => setPanels((prev) => prev.filter((_, i) => i !== idx))}>
                <Trash2 size={14} />
              </button>

              <select
                className={styles.surfaceTagSelect}
                value={p.surfaceTag}
                onChange={(e) => updateSurfaceTag(idx, e.target.value)}
              >
                {surfaceSuggestions.map((st) => (
                  <option key={st} value={st}>
                    {st.toUpperCase()}
                  </option>
                ))}
              </select>
            </motion.div>
          ))}

          {panels.length < 4 && (
            <div className={styles.fileDropArea} onClick={() => document.getElementById('file-upload').click()}>
              <Camera size={28} color="var(--blue-500)" />
              <span className={styles.dropLabel}>{t('take_photo')}</span>
              <span className={styles.dropHint}>{t('choose_gallery')}</span>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileAdd}
                id="file-upload"
                className={styles.hiddenInput}
              />
            </div>
          )}
        </div>

        <Button
          variant="primary"
          icon={ArrowRight}
          disabled={panels.length === 0 || loading}
          onClick={handleScan}
        >
          {t('run_scan_btn')}
        </Button>
      </div>

      {/* 2. Try a Sample Row */}
      {availableSamples.length > 0 && (
        <div className={styles.sampleSection}>
          <div className={styles.sectionHeading}>{t('try_sample_heading')}</div>
          <p className={styles.helperText}>{t('try_sample_sub')}</p>
          <div className={styles.sampleGrid}>
            {availableSamples.map((s) => (
              <div
                key={s.id}
                className={styles.sampleCard}
                onClick={() => handleLoadSample(s.path, s.name)}
              >
                <div className={styles.sampleTitle}>{t(s.titleKey)}</div>
                <div className={styles.sampleDesc}>{t(s.descKey)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. What Gets Checked Panel */}
      <div className={styles.whatGetsCheckedCard}>
        <div className={styles.sectionHeading}>{t('what_gets_checked_heading')}</div>
        <p className={styles.helperText}>{t('what_gets_checked_note')}</p>
        {rulesFetchError ? (
          <div className={styles.mutedReason}>{t('app_rules_fetch_failed')}</div>
        ) : (
          <div className={styles.exampleRulesSection}>
            <div className={styles.exampleRulesTitle}>{t('example_rules_heading')}</div>
            <div className={styles.exampleRulesGrid}>
              {(rulesCatalogue.length > 0
                ? rulesCatalogue.slice(0, 4)
                : [
                    { id: 'R01', rule_ref: 'Rule 6(1)(a)', title_en: 'Manufacturer / Packer / Importer Name & Address', title_hi: 'निर्माता / पैकर / आयातकर्ता का नाम और पता' },
                    { id: 'R02', rule_ref: 'Rule 10(1)', title_en: '6-Digit Postal Index Number (PIN)', title_hi: '6-अंकों का पिन कोड' },
                    { id: 'R04', rule_ref: 'Rule 6(1)(e)', title_en: 'Maximum Retail Price (MRP) & Taxes', title_hi: 'अधिकतम खुदरा मूल्य (MRP) और कर' },
                    { id: 'R07', rule_ref: 'Rule 6(1)(b)', title_en: 'Net Quantity Declaration & Standard Units', title_hi: 'शुद्ध मात्रा घोषणा और मानक इकाइयां' },
                  ]
              ).map((r) => (
                <div key={r.id} className={styles.exampleRuleBox}>
                  <div className={styles.exampleRuleHeader}>
                    <span className={styles.exampleRuleRef}>{r.rule_ref || r.id}</span>
                    <span className={styles.exampleRuleId}>{r.id}</span>
                  </div>
                  <div className={styles.exampleRuleName}>
                    {lang === 'hi' && r.title_hi ? r.title_hi : (r.title_en || r.description || r.id)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 4. Recent Scans in this session (omitted if empty) */}
      {recentScans.length > 0 && (
        <div className={styles.recentScansContainer}>
          <span className={styles.recentTitle}>{t('recent_scans')}:</span>
          <div className={styles.recentRow}>
            {recentScans.map((s) => (
              <span key={s.id} className={styles.recentTag}>
                {s.filename} ({s.time})
              </span>
            ))}
          </div>
        </div>
      )}

      <Toast message={errorMsg} onClose={() => setErrorMsg(null)} />
    </div>
  );
}



