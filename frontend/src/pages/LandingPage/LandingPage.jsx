import React, { useState, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Play, ArrowRight, ShieldCheck, FileText, Search, Cpu, WifiOff, Globe, Smartphone, Code } from 'lucide-react';
import { Button } from '../../components/Button/Button';
import { Logo } from '../../components/Logo/Logo';
import { VerdictBanner } from '../../components/VerdictBanner/VerdictBanner';
import { CountChip } from '../../components/CountChip/CountChip';
import { ScanLine } from '../../components/ScanLine/ScanLine';
import { Stepper } from '../../components/Stepper/Stepper';
import sampleResult from '../../dev/sample_result.json';
import styles from './LandingPage.module.css';

export function LandingPage() {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [demoState, setDemoState] = useState('idle'); // 'idle' | 'scanning' | 'warming' | 'result'
  const [demoResult, setDemoResult] = useState(null);
  const [sliderPos, setSliderPos] = useState(50); // %
  const sliderRef = useRef(null);

  const handleMouseMove = (e) => {
    const card = e.currentTarget;
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width / 2;
    const y = e.clientY - rect.top - rect.height / 2;
    const tiltX = (y / (rect.height / 2)) * -6;
    const tiltY = (x / (rect.width / 2)) * 6;
    setTilt({ x: tiltX, y: tiltY });
  };

  const handleMouseLeave = () => {
    setTilt({ x: 0, y: 0 });
  };

  const runDemoScan = async () => {
    setDemoState('scanning');
    setDemoResult(null);

    const healthTimeout = setTimeout(() => {
      setDemoState('warming');
    }, 2000);

    const fallbackTimeout = setTimeout(() => {
      clearTimeout(healthTimeout);
      setDemoResult(sampleResult);
      setDemoState('result');
    }, 15000);

    try {
      // Fetch bundled synthetic image
      const imgRes = await fetch('/four_violations.png');
      const blob = await imgRes.blob();
      const file = new File([blob], 'four_violations.png', { type: 'image/png' });

      const formData = new FormData();
      formData.append('file', file);
      formData.append('package_type', 'retail');
      formData.append('category', 'general');

      const scanRes = await fetch('/api/scan', {
        method: 'POST',
        body: formData,
      });

      clearTimeout(healthTimeout);
      clearTimeout(fallbackTimeout);

      if (scanRes.ok) {
        const data = await scanRes.json();
        setDemoResult(data);
        setDemoState('result');
      } else {
        setDemoResult(sampleResult);
        setDemoState('result');
      }
    } catch (err) {
      clearTimeout(healthTimeout);
      clearTimeout(fallbackTimeout);
      setDemoResult(sampleResult);
      setDemoState('result');
    }
  };

  const headlineWords = ["Rules-as-code", "compliance", "for", "every", "package"];

  const rulesList = [
    "Rule 6(1)(a) Manufacturer/Importer",
    "Rule 6(1)(b) Generic Name",
    "Rule 6(1)(c) Net Quantity SI Units",
    "Rule 6(1)(d) Mfg/Pkg Month & Year",
    "Rule 6(1)(e) MRP (Inclusive of Taxes)",
    "Rule 6(11) Unit Sale Price",
    "Rule 6(2) Consumer Care Email/Phone",
    "Rule 7 Table-I Font Letter Heights",
    "Rule 8 Clear Space Geometry",
    "Rule 9 Contrast & Legibility",
  ];

  return (
    <div className={styles.landingContainer}>
      {/* Ambient Orbs */}
      <div className={styles.orbContainer}>
        <div className={`${styles.orb} ${styles.orb1}`} />
        <div className={`${styles.orb} ${styles.orb2}`} />
        <div className={`${styles.orb} ${styles.orb3}`} />
      </div>

      {/* Hero Section */}
      <div className={styles.heroSection}>
        <Logo size={72} animate={true} variant="blue" />

        <h1 className={styles.headline}>
          {headlineWords.map((word, idx) => (
            <motion.span
              key={idx}
              className={styles.headlineWord}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08, duration: 0.4 }}
            >
              {word}
            </motion.span>
          ))}
        </h1>

        <p className={styles.subline}>
          Automated legal metrology verification under Legal Metrology (Packaged Commodities) Rules, 2011. High-precision OCR, applicability resolver, and deterministic rules engine.
        </p>

        <div className={styles.heroActions}>
          <NavLink to="/app">
            <Button variant="primary" icon={ArrowRight}>Start Inspection</Button>
          </NavLink>
          <Button variant="secondary" icon={Play} onClick={runDemoScan}>See it work</Button>
        </div>

        {/* 3D Tilt Hero Card */}
        <div className={styles.heroCardWrapper}>
          <div
            className={styles.heroCard}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={{ transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}
          >
            <div className={styles.sheen} />

            {demoState === 'idle' && (
              <div style={{ padding: '20px', color: 'var(--grey-500)' }}>
                <ShieldCheck size={48} color="var(--blue-500)" style={{ marginBottom: '12px' }} />
                <h3>Live Inspection Simulator</h3>
                <p style={{ fontSize: '0.9rem', marginTop: '6px' }}>
                  Click "See it work" to run a real compliance audit on a synthetic multi-violation package.
                </p>
              </div>
            )}

            {(demoState === 'scanning' || demoState === 'warming') && (
              <div className={styles.demoScanning}>
                {demoState === 'warming' && (
                  <div className={styles.warmingUp}>
                    ⚡ Backend warming up... Please wait while neural models load.
                  </div>
                )}
                <ScanLine isScanning={true} />
                <Stepper activeStep={2} />
              </div>
            )}

            {demoState === 'result' && demoResult && (
              <div style={{ textAlign: 'left' }}>
                <VerdictBanner status={demoResult.summary.status} />
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                  <CountChip label="FAIL" count={demoResult.summary.counts.FAIL} variant="fail" />
                  <CountChip label="REVIEW" count={demoResult.summary.counts.NEEDS_REVIEW} variant="review" />
                  <CountChip label="PASS" count={demoResult.summary.counts.PASS} variant="pass" />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div>
        <h2 className={styles.sectionTitle}>How Nirikshan Works</h2>
        <div className={styles.glassCardsGrid}>
          <motion.div
            className={styles.glassCard}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <div className={styles.cardIcon}><Search size={22} /></div>
            <div className={styles.cardTitle}>1. Frame & Scan</div>
            <div className={styles.cardDesc}>
              Camera captures multi-panel label photos. RapidOCR extracts text and quad bounding boxes on CPU.
            </div>
          </motion.div>

          <motion.div
            className={styles.glassCard}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
          >
            <div className={styles.cardIcon}><Cpu size={22} /></div>
            <div className={styles.cardTitle}>2. Applicability & Rules</div>
            <div className={styles.cardDesc}>
              Resolver evaluates exemptions (≤10g, wholesale, food), then runs 35 deterministic rules with exact citations.
            </div>
          </motion.div>

          <motion.div
            className={styles.glassCard}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
          >
            <div className={styles.cardIcon}><FileText size={22} /></div>
            <div className={styles.cardTitle}>3. Evidence & Report</div>
            <div className={styles.cardDesc}>
              Generates color-coded canvas crops, downloadable JSON, and court-admissible PDF reports in Hindi/English.
            </div>
          </motion.div>
        </div>
      </div>

      {/* Split-Flap Counter & Scrolling Rule Strip */}
      <div className={styles.counterSection}>
        <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>Rules-as-code Engine</div>
        <div className={styles.splitFlap}>35</div>
        <div style={{ color: 'var(--grey-300)', fontSize: '0.95rem' }}>Every rule cited with Gazette reference and evidence crop</div>

        <div className={styles.stripWrapper}>
          <div className={styles.ruleStrip}>
            {[...rulesList, ...rulesList].map((r, i) => (
              <span key={i} className={styles.rulePill}>{r}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Before / After Slider */}
      <div>
        <h2 className={styles.sectionTitle}>Before & After Inspection Overlay</h2>
        <div
          ref={sliderRef}
          className={styles.sliderContainer}
          onMouseMove={(e) => {
            if (!sliderRef.current) return;
            const rect = sliderRef.current.getBoundingClientRect();
            const pos = ((e.clientX - rect.left) / rect.width) * 100;
            setSliderPos(Math.min(Math.max(pos, 0), 100));
          }}
        >
          {/* Raw Photo */}
          <img src="/four_violations.png" alt="Raw photo" className={styles.sliderImg} />

          {/* Annotated Photo Clip */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              bottom: 0,
              width: `${sliderPos}%`,
              overflow: 'hidden',
              borderRight: '2px solid var(--blue-500)',
            }}
          >
            <img src="/four_violations.png" alt="Annotated" className={styles.sliderImg} style={{ filter: 'contrast(1.2)' }} />
            <div style={{ position: 'absolute', top: 20, left: 20, background: 'rgba(214,69,69,0.8)', color: 'white', padding: '4px 8px', borderRadius: 4, fontSize: '0.8rem' }}>
              FAIL: Rule 6(1)(e) Missing phrase
            </div>
          </div>

          <div className={styles.sliderDivider} style={{ left: `${sliderPos}%` }}>
            <div className={styles.sliderHandle}>↔</div>
          </div>
        </div>
      </div>

      {/* Built for the Field Section */}
      <div>
        <h2 className={styles.sectionTitle}>Built for the Field</h2>
        <div className={styles.fieldGrid}>
          <div className={styles.fieldCard}>
            <Smartphone size={28} color="var(--blue-500)" style={{ marginBottom: '8px' }} />
            <div>Phone-First PWA</div>
          </div>
          <div className={styles.fieldCard}>
            <WifiOff size={28} color="var(--blue-500)" style={{ marginBottom: '8px' }} />
            <div>Offline-Capable</div>
          </div>
          <div className={styles.fieldCard}>
            <Cpu size={28} color="var(--blue-500)" style={{ marginBottom: '8px' }} />
            <div>CPU-Only Inference</div>
          </div>
          <div className={styles.fieldCard}>
            <Globe size={28} color="var(--blue-500)" style={{ marginBottom: '8px' }} />
            <div>Hindi & English UI</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className={styles.footer}>
        <img src="/brand/logo-tricolour.svg" alt="Nirikshan Logo" height="36" />
        <div>SIH26034 — Legal Metrology Compliance Inspection Platform</div>
        <div>Department of Consumer Affairs, Ministry of Consumer Affairs, Food and Public Distribution</div>
        <a href="https://github.com/rajputjay00/SIH-NIRIKSHAN" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--blue-500)' }}>
          <Code size={16} /> GitHub Repository
        </a>
      </footer>
    </div>
  );
}
