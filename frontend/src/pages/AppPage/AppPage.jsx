import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Upload, AlertTriangle, ArrowRight, Download, Share2, Trash2, CheckCircle2 } from 'lucide-react';
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
import styles from './AppPage.module.css';

export function AppPage() {
  const { t } = useT();
  const reducedMotion = useReducedMotion();
  const [searchParams] = useSearchParams();
  const sessionCode = searchParams.get('session');

  const [panels, setPanels] = useState([]); // [{ file, preview }] up to 4
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [selectedRuleId, setSelectedRuleId] = useState(null);
  const [activeTab, setActiveTab] = useState('findings');
  const [shutterFlash, setShutterFlash] = useState(false);
  const [recentScans, setRecentScans] = useState([]);
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [windowWidth, setWindowWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 800);

  useEffect(() => {
    const handleResize = () => setWindowWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Form Fields for Report
  const [officerName, setOfficerName] = useState(() => localStorage.getItem('nirikshan_officer') || '');
  const [premises, setPremises] = useState(() => localStorage.getItem('nirikshan_premises') || '');
  const [remarks, setRemarks] = useState('');

  // Context Form State
  const [packageType, setPackageType] = useState('retail');
  const [category, setCategory] = useState('general');
  const [isImport, setIsImport] = useState(false);

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

    const newPanel = {
      file: selected,
      preview: URL.createObjectURL(selected),
    };

    setPanels((prev) => [...prev, newPanel]);
  };

  const removePanel = (idx) => {
    setPanels((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleScan = async (e) => {
    if (e) e.preventDefault();
    if (panels.length === 0) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const scaledFile = await downscaleImage(panels[0].file, 2400);
      const data = await scanImage(scaledFile, {
        packageType,
        category,
        isImport,
        session: sessionCode,
      });

      setScanResult(data);
      setRecentScans((prev) => [
        { id: Date.now(), filename: data.filename || panels[0].file.name, status: data.summary.status, time: new Date().toLocaleTimeString() },
        ...prev.slice(0, 4),
      ]);
    } catch (err) {
      setErrorMsg('Error scanning label. Ensure format is JPEG/PNG/WebP and under 10 MB.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = async () => {
    if (!scanResult) return;
    setPdfDownloading(true);
    try {
      localStorage.setItem('nirikshan_officer', officerName);
      localStorage.setItem('nirikshan_premises', premises);

      const formData = new FormData();
      formData.append('file', panels[0].file);
      formData.append('scan_result', JSON.stringify(scanResult));
      formData.append('officer_name', officerName);
      formData.append('premises', premises);
      formData.append('remarks', remarks);

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
    } catch (err) {
      setErrorMsg('Failed to download PDF report');
    } finally {
      setPdfDownloading(false);
    }
  };

  const handleDownloadJSON = () => {
    if (!scanResult) return;
    const blob = new Blob([JSON.stringify(scanResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nirikshan_scan_${scanResult.filename || 'scan'}.json`;
    a.click();
  };

  const handleShare = async () => {
    if (navigator.share && scanResult) {
      try {
        await navigator.share({
          title: 'Nirikshan Compliance Verdict',
          text: `Verdict: ${scanResult.summary.status} | Legal Metrology Rules Review`,
          url: window.location.href,
        });
      } catch (err) {
        // user cancelled share
      }
    } else {
      navigator.clipboard.writeText(window.location.href);
      setErrorMsg('Verdict URL copied to clipboard');
    }
  };

  const qualityWarnings = scanResult?.quality?.warnings || [];
  const applicableFindings = scanResult?.findings?.filter((f) => f.verdict !== 'N/A') || [];
  const naFindings = scanResult?.findings?.filter((f) => f.verdict === 'N/A') || [];
  const selectedFinding = scanResult?.findings?.find((f) => f.rule_id === selectedRuleId);

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

      {/* Upload Card & Context */}
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
        </div>

        <div className={styles.sectionHeading}>2. Label Photo Panels (Up to 4)</div>
        
        {/* Thumbnails Row */}
        <div className={styles.thumbnailsRow}>
          {panels.map((p, idx) => (
            <motion.div
              key={idx}
              className={styles.thumbWrapper}
              layoutId={idx === 0 ? "scan-hero-image" : undefined}
              initial={reducedMotion ? { opacity: 1 } : { scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              <img src={p.preview} alt={`Panel ${idx + 1}`} className={styles.thumbImg} />
              <button type="button" className={styles.removeBtn} onClick={() => removePanel(idx)}>
                <Trash2 size={14} />
              </button>
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

      {/* Recent Scans (Session State) */}
      {recentScans.length > 0 && (
        <div className={styles.recentScansContainer}>
          <span className={styles.recentTitle}>{t('recent_scans')}:</span>
          <div className={styles.recentRow}>
            {recentScans.map((s) => (
              <span key={s.id} className={styles.recentTag}>
                {s.filename} ({s.status})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Loading Scan State */}
      {loading && (
        <div className={styles.scanSection}>
          <ScanLine isScanning={true} />
          <Stepper activeStep={2} />
        </div>
      )}

      {/* Results View */}
      {scanResult && !loading && (
        <div>
          {/* Verdict Banner with Hero layoutId */}
          <motion.div layoutId="scan-hero-image">
            <VerdictBanner
              status={scanResult.summary.status}
              exemptReason={scanResult.applicability.exempt_reason}
            />
          </motion.div>

          {/* Counts Header */}
          <div className={styles.resultHeader}>
            <div className={styles.countsRow}>
              <CountChip label={t('count_fail')} count={scanResult.summary.counts.FAIL} variant="fail" />
              <CountChip label={t('count_review')} count={scanResult.summary.counts.NEEDS_REVIEW} variant="review" />
              <CountChip label={t('count_pass')} count={scanResult.summary.counts.PASS} variant="pass" />
              <CountChip label={t('count_na')} count={scanResult.summary.counts['N/A']} variant="na" />
            </div>
          </div>

          {/* Quality Warning Ribbon */}
          {qualityWarnings.length > 0 && (
            <div className={styles.qualityWarning}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertTriangle size={18} />
                <span>Quality Warning: {qualityWarnings.join(', ')}</span>
              </div>
              <Button variant="ghost" onClick={() => document.getElementById('file-upload').click()}>
                {t('retake_photo')}
              </Button>
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
                    <RuleCard key={f.rule_id} finding={f} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Evidence Tab */}
          {activeTab === 'evidence' && (
            <div className={styles.evidenceLayout}>
              <EvidenceCanvas
                imageSrc={panels[0]?.preview}
                scanResult={scanResult}
                selectedRuleId={selectedRuleId}
                onSelectRule={setSelectedRuleId}
              />

              {/* Desktop Side Highlight */}
              {windowWidth >= 640 && selectedFinding && (
                <div className={styles.desktopSidePanel}>
                  <h4 style={{ marginBottom: '12px', color: 'var(--navy-900)' }}>Selected Rule Details</h4>
                  <RuleCard finding={selectedFinding} />
                </div>
              )}

              {/* Mobile BottomSheet (<640px) */}
              {windowWidth < 640 && (
                <BottomSheet isOpen={Boolean(selectedFinding)} onClose={() => setSelectedRuleId(null)}>
                  {selectedFinding && <RuleCard finding={selectedFinding} />}
                </BottomSheet>
              )}
            </div>
          )}

          {/* Declarations Tab */}
          {activeTab === 'declarations' && (
            <div className={styles.declGrid}>
              {scanResult.declarations.multi_unit_note && (
                <div className={styles.multiUnitCallout}>
                  <AlertTriangle size={18} />
                  <span>Multi-unit declaration applies: Each individual unit inside package must declare MRP and net quantity.</span>
                </div>
              )}

              <DeclarationCard label="Net Quantity" field={scanResult.declarations.net_quantity} />
              <DeclarationCard label="MRP" field={scanResult.declarations.mrp} />
              <DeclarationCard label="Unit Sale Price" field={scanResult.declarations.unit_sale_price} />
              <DeclarationCard label="Generic Name" field={scanResult.declarations.generic_name} />
              <DeclarationCard label="Mfg Date" field={scanResult.declarations.mfg_date} />
              <DeclarationCard label="Best Before" field={scanResult.declarations.best_before} />
              <DeclarationCard label="Country of Origin" field={scanResult.declarations.country_of_origin} />

              {scanResult.declarations.importer && (
                <EntityCard entity={scanResult.declarations.importer} />
              )}
              {scanResult.declarations.manufacturer && (
                <EntityCard entity={scanResult.declarations.manufacturer} />
              )}
              {(scanResult.declarations.entities || []).map((ent, idx) => (
                <EntityCard key={idx} entity={ent} />
              ))}
            </div>
          )}

          {/* Report Tab */}
          {activeTab === 'report' && (
            <div className={styles.reportForm}>
              <div className={styles.formGroup}>
                <label>{t('officer_name')}</label>
                <input
                  type="text"
                  value={officerName}
                  onChange={(e) => setOfficerName(e.target.value)}
                  placeholder="Inspector Sharma"
                  className={styles.inputField}
                />
              </div>

              <div className={styles.formGroup}>
                <label>{t('premises_location')}</label>
                <input
                  type="text"
                  value={premises}
                  onChange={(e) => setPremises(e.target.value)}
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
                  <Button variant="primary" icon={Download} disabled={pdfDownloading} onClick={handleDownloadPDF}>
                    {pdfDownloading ? 'Generating PDF...' : t('download_pdf')}
                  </Button>
                  {pdfDownloading && <div className={styles.inkFillProgress} />}
                </div>
                <Button variant="secondary" icon={Download} onClick={handleDownloadJSON}>
                  {t('download_json')}
                </Button>
                <Button variant="ghost" icon={Share2} onClick={handleShare}>
                  {t('share_report')}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      <Toast message={errorMsg} onClose={() => setErrorMsg(null)} />
    </div>
  );
}

