import React, { useState } from 'react';
import { Camera, Upload, AlertTriangle, ArrowRight } from 'lucide-react';
import { scanImage } from '../../api';
import { useT } from '../../i18n/useT';
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
import styles from './AppPage.module.css';

export function AppPage() {
  const { t } = useT();

  const [file, setFile] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [selectedRuleId, setSelectedRuleId] = useState(null);
  const [activeTab, setActiveTab] = useState('findings');

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

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setImageSrc(URL.createObjectURL(selected));
      setScanResult(null);
      setSelectedRuleId(null);
    }
  };

  const handleScan = async (e) => {
    if (e) e.preventDefault();
    if (!file) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await scanImage(file, {
        packageType,
        category,
        isImport,
      });
      setScanResult(data);
    } catch (err) {
      setErrorMsg('Error scanning label. Ensure format is JPEG/PNG/WebP and under 10 MB.');
    } finally {
      setLoading(false);
    }
  };

  const qualityWarnings = scanResult?.quality?.warnings || [];
  const applicableFindings = scanResult?.findings?.filter((f) => f.verdict !== 'N/A') || [];
  const naFindings = scanResult?.findings?.filter((f) => f.verdict === 'N/A') || [];

  return (
    <div className={styles.appPage}>
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

        <div className={styles.sectionHeading}>2. Label Photo</div>
        <div className={styles.fileDropArea} onClick={() => document.getElementById('file-upload').click()}>
          <Camera size={32} color="var(--blue-500)" />
          <span className={styles.dropLabel}>{file ? file.name : t('take_photo')}</span>
          <span className={styles.dropHint}>{t('choose_gallery')}</span>
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileChange}
            id="file-upload"
            className={styles.hiddenInput}
          />
        </div>

        <Button
          variant="primary"
          icon={ArrowRight}
          disabled={!file || loading}
          onClick={handleScan}
        >
          {t('run_scan_btn')}
        </Button>
      </div>

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
          {/* Verdict Banner */}
          <VerdictBanner
            status={scanResult.summary.status}
            exemptReason={scanResult.applicability.exempt_reason}
          />

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
            <EvidenceCanvas
              imageSrc={imageSrc}
              scanResult={scanResult}
              selectedRuleId={selectedRuleId}
              onSelectRule={setSelectedRuleId}
            />
          )}

          {/* Declarations Tab */}
          {activeTab === 'declarations' && (
            <div className={styles.declGrid}>
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
            </div>
          )}
        </div>
      )}

      <Toast message={errorMsg} onClose={() => setErrorMsg(null)} />
    </div>
  );
}
