import React, { useState } from 'react';
import sampleResult from '../../dev/sample_result.json';
import { Button } from '../../components/Button/Button';
import { Chip } from '../../components/Chip/Chip';
import { Card, GlassCard } from '../../components/Card/Card';
import { VerdictBanner } from '../../components/VerdictBanner/VerdictBanner';
import { CountChip } from '../../components/CountChip/CountChip';
import { RuleCard } from '../../components/RuleCard/RuleCard';
import { EvidenceCanvas } from '../../components/EvidenceCanvas/EvidenceCanvas';
import { DeclarationCard } from '../../components/DeclarationCard/DeclarationCard';
import { EntityCard } from '../../components/EntityCard/EntityCard';
import { Stepper } from '../../components/Stepper/Stepper';
import { ScanLine } from '../../components/ScanLine/ScanLine';
import { Tabs } from '../../components/Tabs/Tabs';
import { BottomSheet } from '../../components/BottomSheet/BottomSheet';
import { Drawer } from '../../components/Drawer/Drawer';
import { Toast } from '../../components/Toast/Toast';
import { Skeleton } from '../../components/Skeleton/Skeleton';
import { LanguageToggle } from '../../components/LanguageToggle/LanguageToggle';
import { StatusDot } from '../../components/StatusDot/StatusDot';
import { QRPair } from '../../components/QRPair/QRPair';
import { Logo } from '../../components/Logo/Logo';
import styles from './DevComponents.module.css';

export function DevComponents() {
  const [activeTab, setActiveTab] = useState('findings');
  const [selectedChip, setSelectedChip] = useState('retail');
  const [showSheet, setShowSheet] = useState(false);
  const [showDrawer, setShowDrawer] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);
  const [selectedRuleId, setSelectedRuleId] = useState('R02');

  return (
    <div className={styles.devPage}>
      <h2>UI Component Gallery (/dev/components)</h2>

      {/* 0. Government Console Shell Header & Brand Lockup */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>0. Government Console Shell Chrome</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--white)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--grey-100)' }}>
          <div style={{ background: 'var(--navy-900)', color: 'var(--white)', padding: '6px 16px', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem', display: 'flex', justifyContent: 'space-between' }}>
            <span>NIRIKSHAN · Legal Metrology Compliance &amp; Inspection System</span>
            <span>EN | Backend Online</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <img src="/brand/mark-blue.svg" alt="Nirikshan Logo" height="32" />
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: '1.1' }}>
                <span style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--navy-900)' }}>NIRIKSHAN</span>
                <span style={{ fontSize: '0.62rem', fontWeight: 600, color: 'var(--grey-500)', letterSpacing: '0.06em' }}>
                  LEGAL METROLOGY COMPLIANCE<br />&amp; INSPECTION SYSTEM
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 12px', background: 'var(--grey-100)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--grey-300)' }}>
              <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Inspector J. Rajput</span>
            </div>
          </div>
        </div>
      </div>

      {/* 1. Logo */}

      <div className={styles.section}>
        <div className={styles.sectionTitle}>1. Logo</div>
        <div className={styles.row}>
          <Logo size={48} animate={true} variant="blue" />
          <Logo size={48} animate={true} variant="tricolour" />
        </div>
      </div>

      {/* 2. Buttons */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>2. Buttons</div>
        <div className={styles.row}>
          <Button variant="primary">Primary Button</Button>
          <Button variant="secondary">Secondary Button</Button>
          <Button variant="ghost">Ghost Button</Button>
          <Button variant="primary" disabled>Disabled</Button>
        </div>
      </div>

      {/* 3. Chips */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>3. Chips</div>
        <div className={styles.row}>
          <Chip selected={selectedChip === 'retail'} onClick={() => setSelectedChip('retail')}>
            Retail Package
          </Chip>
          <Chip selected={selectedChip === 'wholesale'} onClick={() => setSelectedChip('wholesale')}>
            Wholesale Package
          </Chip>
          <Chip selected={selectedChip === 'import'} onClick={() => setSelectedChip('import')}>
            Imported Commodity
          </Chip>
        </div>
      </div>

      {/* 4. Cards */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>4. Card &amp; GlassCard</div>
        <div className={styles.grid}>
          <Card>
            <h4>Standard Card</h4>
            <p>Solid white background with soft shadow.</p>
          </Card>
          <GlassCard>
            <h4>Glass Card</h4>
            <p>Translucent glassmorphism background.</p>
          </GlassCard>
        </div>
      </div>

      {/* 5. Verdict Banners */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>5. Verdict Banners</div>
        <VerdictBanner status="Compliant" />
        <VerdictBanner status="Non-compliant" />
        <VerdictBanner status="Officer Review Required" />
        <VerdictBanner status="Compliant (after officer confirmation)" />
        <VerdictBanner status="Exempt" exemptReason="Rule 26(a): Package <= 10g exempt from all declarations" />
        <VerdictBanner status="Compliant" isWholesale={true} />
      </div>

      {/* 6. Count Chips */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>6. Count Chips</div>
        <div className={styles.row}>
          <CountChip label="FAIL" count={sampleResult.summary.counts.FAIL} variant="fail" />
          <CountChip label="REVIEW" count={sampleResult.summary.counts.NEEDS_REVIEW} variant="review" />
          <CountChip label="PASS" count={sampleResult.summary.counts.PASS} variant="pass" />
          <CountChip label="N/A" count={sampleResult.summary.counts['N/A']} variant="na" />
        </div>
      </div>

      {/* 7. Stepper */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>7. Stepper &amp; ScanLine</div>
        <Stepper activeStep={2} />
        <div style={{ position: 'relative', height: '80px', backgroundColor: 'var(--navy-900)', borderRadius: 'var(--radius-md)' }}>
          <ScanLine isScanning={true} />
        </div>
      </div>

      {/* 8. Tabs */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>8. Tabs</div>
        <Tabs
          tabs={[
            { id: 'findings', label: 'Findings' },
            { id: 'evidence', label: 'Evidence' },
            { id: 'declarations', label: 'Declarations' },
            { id: 'report', label: 'Report' },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {/* 9. Rule Cards */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>9. Rule Cards (Sample Findings)</div>
        {sampleResult.findings.slice(0, 3).map((f) => (
          <RuleCard
            key={f.rule_id}
            finding={f}
            onShowOnImage={(rid) => {
              setSelectedRuleId(rid);
              setToastMsg(`Selected rule ${rid} on canvas`);
            }}
          />
        ))}
      </div>

      {/* 10. Declaration & Entity Cards */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>10. Declaration &amp; Entity Cards</div>
        <div className={styles.grid}>
          <DeclarationCard label="Net Quantity" field={sampleResult.declarations.net_quantity} />
          <DeclarationCard label="MRP" field={sampleResult.declarations.mrp} />
          <EntityCard entity={sampleResult.declarations.importer} />
        </div>
      </div>

      {/* 11. StatusDot & LanguageToggle */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>11. StatusDot &amp; LanguageToggle</div>
        <div className={styles.row}>
          <StatusDot isOnline={true} />
          <StatusDot isOnline={false} />
          <LanguageToggle />
        </div>
      </div>

      {/* 12. QRPair & Skeleton */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>12. QRPair &amp; Skeleton</div>
        <div className={styles.row}>
          <QRPair pairCode="NRK-9921" />
          <div style={{ width: '200px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <Skeleton height="30px" />
            <Skeleton height="16px" />
            <Skeleton height="16px" width="70%" />
          </div>
        </div>
      </div>

      {/* 13. Modals & Overlays */}
      <div className={styles.section}>
        <div className={styles.sectionTitle}>13. Modals &amp; Interactive Triggers</div>
        <div className={styles.row}>
          <Button onClick={() => setShowSheet(true)}>Open Bottom Sheet</Button>
          <Button variant="secondary" onClick={() => setShowDrawer(true)}>Open Drawer</Button>
          <Button variant="ghost" onClick={() => setToastMsg('Sample notification error toast')}>Trigger Toast</Button>
        </div>
      </div>

      <BottomSheet isOpen={showSheet} onClose={() => setShowSheet(false)}>
        <h3>Bottom Sheet Content</h3>
        <p>Drag down to dismiss or tap backdrop.</p>
        <Button onClick={() => setShowSheet(false)}>Close</Button>
      </BottomSheet>

      <Drawer isOpen={showDrawer} onClose={() => setShowDrawer(false)} title="Rule Detail Drawer">
        <p>Full rule explanation, source text, and fix recommendations.</p>
        <Button onClick={() => setShowDrawer(false)}>Close Drawer</Button>
      </Drawer>

      <Toast message={toastMsg} onClose={() => setToastMsg(null)} />
    </div>
  );
}
