import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, RefreshCw, Smartphone, Layers } from 'lucide-react';
import { QRPair } from '../../components/QRPair/QRPair';
import { Button } from '../../components/Button/Button';
import { VerdictBanner } from '../../components/VerdictBanner/VerdictBanner';
import { CountChip } from '../../components/CountChip/CountChip';
import { RuleCard } from '../../components/RuleCard/RuleCard';
import { EvidenceCanvas } from '../../components/EvidenceCanvas/EvidenceCanvas';
import { DeclarationCard } from '../../components/DeclarationCard/DeclarationCard';
import { EntityCard } from '../../components/EntityCard/EntityCard';
import { Tabs } from '../../components/Tabs/Tabs';
import { scanImage } from '../../api';
import { useT } from '../../i18n/useT';
import styles from './ReviewPage.module.css';

export function ReviewPage() {
  const { t } = useT();

  const [sessionCode, setSessionCode] = useState('');
  const [inputCode, setInputCode] = useState('');
  const [scans, setScans] = useState([]);
  const [selectedScanId, setSelectedScanId] = useState(null);
  const [activeTab, setActiveTab] = useState('findings');
  const [selectedRuleId, setSelectedRuleId] = useState(null);
  const [loading, setLoading] = useState(false);

  const createNewSession = async () => {
    try {
      const res = await fetch('/api/session', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSessionCode(data.code);
        setInputCode(data.code);
        setScans([]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    createNewSession();
  }, []);

  // Poll / SSE for session results
  useEffect(() => {
    if (!sessionCode) return;

    const fetchResults = async () => {
      try {
        const res = await fetch(`/api/session/${sessionCode}/results`);
        if (res.ok) {
          const list = await res.json();
          setScans(list);
          if (list.length > 0 && !selectedScanId) {
            setSelectedScanId(list[0].id);
          }
        }
      } catch (err) {
        // quiet
      }
    };

    fetchResults();
    const interval = setInterval(fetchResults, 3000);
    return () => clearInterval(interval);
  }, [sessionCode, selectedScanId]);

  const handleManualPair = (e) => {
    e.preventDefault();
    if (inputCode.trim()) {
      setSessionCode(inputCode.trim().toUpperCase());
      setScans([]);
      setSelectedScanId(null);
    }
  };

  const handleFallbackUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    try {
      const data = await scanImage(file, { session: sessionCode });
      const newScan = {
        id: `scan_${Date.now()}`,
        result: data,
        thumbnail_jpeg_b64: null,
        created_at: new Date().toISOString(),
      };
      setScans((prev) => [newScan, ...prev]);
      setSelectedScanId(newScan.id);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const activeScan = scans.find((s) => s.id === selectedScanId) || scans[0];
  const activeResult = activeScan?.result;
  const pairUrl = typeof window !== 'undefined' ? `${window.location.origin}/app?session=${sessionCode}` : '';

  const applicableFindings = activeResult?.findings?.filter((f) => f.verdict !== 'N/A') || [];
  const naFindings = activeResult?.findings?.filter((f) => f.verdict === 'N/A') || [];

  return (
    <div className={styles.reviewContainer}>
      {/* Left Column: Pairing & Scans Stack */}
      <div className={styles.leftColumn}>
        <div className={styles.pairingCard}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700 }}>
            <Smartphone size={20} color="var(--blue-500)" />
            <span>Phone Pairing</span>
          </div>

          {sessionCode && <QRPair pairCode={sessionCode} url={pairUrl} />}

          <form onSubmit={handleManualPair} className={styles.codeForm}>
            <input
              type="text"
              value={inputCode}
              onChange={(e) => setInputCode(e.target.value)}
              placeholder="CODE"
              className={styles.codeInput}
              maxLength={6}
            />
            <Button type="submit" variant="secondary">Pair</Button>
          </form>

          <Button variant="ghost" icon={RefreshCw} onClick={createNewSession}>
            New Code
          </Button>
        </div>

        {/* Scans List */}
        {scans.length > 0 && (
          <div className={styles.scansList}>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--navy-900)' }}>
              Incoming Inspection Scans ({scans.length})
            </div>
            {scans.map((scan) => {
              const isSelected = scan.id === selectedScanId;
              const res = scan.result;
              return (
                <motion.div
                  key={scan.id}
                  className={`${styles.scanItem} ${isSelected ? styles.selectedItem : ''}`}
                  onClick={() => setSelectedScanId(scan.id)}
                  initial={{ x: -20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                >
                  {scan.thumbnail_jpeg_b64 ? (
                    <img
                      src={`data:image/jpeg;base64,${scan.thumbnail_jpeg_b64}`}
                      alt="Thumbnail"
                      className={styles.scanThumb}
                    />
                  ) : (
                    <div className={styles.scanThumb} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Layers size={20} color="var(--grey-500)" />
                    </div>
                  )}

                  <div className={styles.scanMeta}>
                    <span className={styles.scanName}>{res.filename || 'Scan'}</span>
                    <span style={{ color: 'var(--grey-500)' }}>{res.summary?.status}</span>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Fallback Upload */}
        <div className={styles.dropZone} onClick={() => document.getElementById('review-upload').click()}>
          <Upload size={24} style={{ marginBottom: '4px' }} />
          <div>Or drag/upload image here</div>
          <input
            type="file"
            accept="image/*"
            onChange={handleFallbackUpload}
            id="review-upload"
            style={{ display: 'none' }}
          />
        </div>
      </div>

      {/* Right Column: Desktop Result Layout */}
      <div className={styles.rightColumn}>
        {activeResult ? (
          <div>
            <VerdictBanner
              status={activeResult.summary.status}
              exemptReason={activeResult.applicability.exempt_reason}
            />

            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <CountChip label={t('count_fail')} count={activeResult.summary.counts.FAIL} variant="fail" />
              <CountChip label={t('count_review')} count={activeResult.summary.counts.NEEDS_REVIEW} variant="review" />
              <CountChip label={t('count_pass')} count={activeResult.summary.counts.PASS} variant="pass" />
              <CountChip label={t('count_na')} count={activeResult.summary.counts['N/A']} variant="na" />
            </div>

            <Tabs
              tabs={[
                { id: 'findings', label: t('tab_findings') },
                { id: 'evidence', label: t('tab_evidence') },
                { id: 'declarations', label: t('tab_declarations') },
              ]}
              activeTab={activeTab}
              onChange={setActiveTab}
            />

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
                  <div style={{ marginTop: '16px' }}>
                    <h4>{t('not_applicable_header')} ({naFindings.length})</h4>
                    {naFindings.map((f) => (
                      <RuleCard key={f.rule_id} finding={f} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'evidence' && (
              <EvidenceCanvas
                imageSrc={activeScan.thumbnail_jpeg_b64 ? `data:image/jpeg;base64,${activeScan.thumbnail_jpeg_b64}` : null}
                scanResult={activeResult}
                selectedRuleId={selectedRuleId}
                onSelectRule={setSelectedRuleId}
              />
            )}

            {activeTab === 'declarations' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                <DeclarationCard label="Net Quantity" field={activeResult.declarations.net_quantity} />
                <DeclarationCard label="MRP" field={activeResult.declarations.mrp} />
                <DeclarationCard label="Unit Sale Price" field={activeResult.declarations.unit_sale_price} />
                <DeclarationCard label="Generic Name" field={activeResult.declarations.generic_name} />
                <DeclarationCard label="Mfg Date" field={activeResult.declarations.mfg_date} />
                <DeclarationCard label="Best Before" field={activeResult.declarations.best_before} />
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--grey-500)' }}>
            <h3>Waiting for inspection scans...</h3>
            <p>Scan a product label using your paired phone or upload an image on the left.</p>
          </div>
        )}
      </div>
    </div>
  );
}
