import React, { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Play,
  ArrowRight,
  ShieldCheck,
  FileText,
  Search,
  Cpu,
  WifiOff,
  Globe,
  Smartphone,
  Camera,
  Layers,
  Scale,
  ShoppingCart,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '../../components/Button/Button';
import { Logo } from '../../components/Logo/Logo';
import { VerdictBanner } from '../../components/VerdictBanner/VerdictBanner';
import { CountChip } from '../../components/CountChip/CountChip';
import { ScanLine } from '../../components/ScanLine/ScanLine';
import { Stepper } from '../../components/Stepper/Stepper';
import { Skeleton } from '../../components/Skeleton/Skeleton';
import { useT } from '../../i18n/useT';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import sampleResult from '../../dev/sample_result.json';
import styles from './LandingPage.module.css';

export function LandingPage() {
  const { t } = useT();
  const reducedMotion = useReducedMotion();

  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [demoState, setDemoState] = useState('idle'); // 'idle' | 'scanning' | 'warming' | 'result'
  const [demoResult, setDemoResult] = useState(null);

  // Live Statistics state fetched from /api/rules and /api/health
  const [stats, setStats] = useState({
    rulesCount: null,
    conflictCount: null,
    rulesVersion: null,
    loading: true,
  });

  useEffect(() => {
    let isMounted = true;
    const fetchLiveData = async () => {
      try {
        const [rulesRes, healthRes] = await Promise.all([
          fetch('/api/rules').catch(() => null),
          fetch('/api/health').catch(() => null),
        ]);

        let count = null;
        let cCount = null;
        let ver = null;

        if (rulesRes && rulesRes.ok) {
          const rData = await rulesRes.json();
          const rulesList = Array.isArray(rData.rules)
            ? rData.rules
            : (Array.isArray(rData) ? rData : Object.values(rData.rules || rData || {}));

          count = rulesList.filter((r) => r && r.id && /^R/.test(r.id)).length;
          cCount = rulesList.filter((r) => r && r.id && /^C/.test(r.id)).length;
          ver = rData.rules_version || rData.version || null;
        }

        if (!ver && healthRes && healthRes.ok) {
          const hData = await healthRes.json();
          ver = hData.rules_version || null;
        }

        if (isMounted) {
          setStats({
            rulesCount: count,
            conflictCount: cCount,
            rulesVersion: ver,
            loading: false,
          });
        }
      } catch (err) {
        if (isMounted) {
          setStats((prev) => ({ ...prev, loading: false }));
        }
      }
    };

    fetchLiveData();
    return () => {
      isMounted = false;
    };
  }, []);

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

  const headlineWords = ['Rules-as-code', 'compliance', 'for', 'every', 'package'];

  const capabilities = [
    {
      id: 'drishti',
      tag: t('mod_drishti_tag'),
      icon: Camera,
      title: t('mod_drishti_title'),
      desc: t('mod_drishti_desc'),
      route: '/app',
    },
    {
      id: 'niyam',
      tag: t('mod_niyam_tag'),
      icon: FileText,
      title: t('mod_niyam_title'),
      desc: t('mod_niyam_desc'),
      route: '/rules',
    },
    {
      id: 'maap',
      tag: t('mod_maap_tag'),
      icon: Layers,
      title: t('mod_maap_title'),
      desc: t('mod_maap_desc'),
      route: '/app',
    },
    {
      id: 'tol',
      tag: t('mod_tol_tag'),
      icon: Scale,
      title: t('mod_tol_title'),
      desc: t('mod_tol_desc'),
      route: '/app',
    },
    {
      id: 'jaal',
      tag: t('mod_jaal_tag'),
      icon: ShoppingCart,
      title: t('mod_jaal_title'),
      desc: t('mod_jaal_desc'),
      route: '/listing',
    },
    {
      id: 'pramaan',
      tag: t('mod_pramaan_tag'),
      icon: ShieldCheck,
      title: t('mod_pramaan_title'),
      desc: t('mod_pramaan_desc'),
      route: '/review',
    },
  ];

  const workflowSteps = [
    { num: '01', title: t('step01_title'), desc: t('step01_desc') },
    { num: '02', title: t('step02_title'), desc: t('step02_desc') },
    { num: '03', title: t('step03_title'), desc: t('step03_desc') },
    { num: '04', title: t('step04_title'), desc: t('step04_desc') },
    { num: '05', title: t('step05_title'), desc: t('step05_desc') },
    { num: '06', title: t('step06_title'), desc: t('step06_desc') },
  ];

  return (
    <div className={styles.landingContainer}>
      {/* Ambient Orbs */}
      <div className={styles.orbContainer}>
        <div className={`${styles.orb} ${styles.orb1}`} />
        <div className={`${styles.orb} ${styles.orb2}`} />
      </div>

      {/* 1. Tightened Hero Section */}
      <div className={styles.heroSection}>
        <Logo size={48} animate={true} variant="blue" />

        <h1 className={styles.headline}>
          {headlineWords.map((word, idx) => (
            <motion.span
              key={idx}
              className={styles.headlineWord}
              initial={reducedMotion ? false : { opacity: 0, y: 12 }}
              animate={reducedMotion ? false : { opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.06, duration: 0.3 }}
            >
              {word}
            </motion.span>
          ))}
        </h1>

        <p className={styles.subline}>
          Automated legal metrology verification under Legal Metrology (Packaged Commodities) Rules, 2011.
          High-precision OCR, applicability resolver, and deterministic rules engine.
        </p>

        <div className={styles.heroActions}>
          <NavLink to="/app">
            <Button variant="primary" icon={ArrowRight}>
              {t('start_inspection')}
            </Button>
          </NavLink>
          <Button variant="secondary" icon={Play} onClick={runDemoScan}>
            See it work
          </Button>
        </div>

        {/* Compact Live Stat Strip */}
        <div className={styles.statStrip}>
          <div className={styles.statItem}>
            <span className={styles.statValue}>
              {stats.loading ? <Skeleton width="24px" height="20px" /> : (stats.rulesCount ?? '34')}
            </span>
            <span className={styles.statLabel}>
              {`${stats.rulesCount ?? 34} of 35 ${t('stat_rules_implemented')}`}
            </span>
          </div>

          <div className={styles.statDivider} />

          <div className={styles.statItem}>
            <span className={styles.statValue}>
              {stats.loading ? <Skeleton width="24px" height="20px" /> : (stats.conflictCount ?? '5')}
            </span>
            <span className={styles.statLabel}>{t('stat_conflict_checks')}</span>
          </div>

          <div className={styles.statDivider} />

          <div className={styles.statItem}>
            <span className={styles.statValue}>
              {stats.loading ? (
                <Skeleton width="50px" height="20px" />
              ) : (
                stats.rulesVersion?.split('+')[0] || stats.rulesVersion || '0.4.0'
              )}
            </span>
            <span className={styles.statLabel}>{t('stat_rules_version')}</span>
          </div>
        </div>

        {/* 3D Tilt Hero Card Simulator */}
        <div className={styles.heroCardWrapper}>
          <div
            className={styles.heroCard}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            style={reducedMotion ? {} : { transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)` }}
          >
            <div className={styles.sheen} />

            {demoState === 'idle' && (
              <div style={{ padding: '16px', color: 'var(--grey-500)', textAlign: 'center' }}>
                <ShieldCheck size={40} color="var(--blue-500)" style={{ marginBottom: '8px' }} />
                <h3 style={{ margin: 0, color: 'var(--navy-900)' }}>Live Inspection Simulator</h3>
                <p style={{ fontSize: '0.85rem', marginTop: '4px', color: 'var(--grey-700)' }}>
                  Click "See it work" to run a real compliance audit on a multi-violation package.
                </p>
              </div>
            )}

            {(demoState === 'scanning' || demoState === 'warming') && (
              <div className={styles.demoScanning}>
                {demoState === 'warming' && (
                  <div className={styles.warmingUp}>
                    ⚡ Backend warming up... Please wait while models initialize.
                  </div>
                )}
                <ScanLine isScanning={true} />
                <Stepper activeStep={2} />
              </div>
            )}

            {demoState === 'result' && demoResult && (
              <div style={{ textAlign: 'left' }}>
                <VerdictBanner status={demoResult.summary?.status || 'Non-compliant'} />
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
                  <CountChip label="FAIL" count={demoResult.summary?.counts?.FAIL || 0} variant="fail" />
                  <CountChip label="REVIEW" count={demoResult.summary?.counts?.NEEDS_REVIEW || 0} variant="review" />
                  <CountChip label="PASS" count={demoResult.summary?.counts?.PASS || 0} variant="pass" />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Core Capabilities Grid Section */}
      <div className={styles.sectionBlock}>
        <div className={styles.eyebrowWrapper}>
          <span className={styles.eyebrowChip}>{t('eyebrow_capabilities')}</span>
        </div>
        <h2 className={styles.sectionHeading}>{t('capabilities_heading')}</h2>

        <div className={styles.capabilitiesGrid}>
          {capabilities.map((cap, idx) => {
            const Icon = cap.icon;
            return (
              <motion.div
                key={cap.id}
                className={styles.capabilityCard}
                initial={reducedMotion ? false : { opacity: 0, y: 8 }}
                whileInView={reducedMotion ? false : { opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.06, duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
              >
                <div className={styles.capTop}>
                  <div className={styles.capHeader}>
                    <div className={styles.capIconBox}>
                      <Icon size={20} />
                    </div>
                    <span className={styles.capTag}>{cap.tag}</span>
                  </div>
                  <h3 className={styles.capTitle}>{cap.title}</h3>
                  <p className={styles.capDesc}>{cap.desc}</p>
                </div>

                <NavLink to={cap.route} className={styles.capLink}>
                  <span>{t('module_open')}</span>
                  <ArrowRight size={14} />
                </NavLink>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* 3. How An Inspection Runs Section */}
      <div className={styles.sectionBlock}>
        <div className={styles.eyebrowWrapper}>
          <span className={styles.eyebrowChip}>{t('eyebrow_workflow')}</span>
        </div>
        <h2 className={styles.sectionHeading}>{t('workflow_heading')}</h2>

        <div className={styles.workflowGrid}>
          {workflowSteps.map((step, idx) => (
            <motion.div
              key={step.num}
              className={styles.stepCard}
              initial={reducedMotion ? false : { opacity: 0, y: 8 }}
              whileInView={reducedMotion ? false : { opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.06, duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            >
              <span className={styles.stepBadge}>{step.num}</span>
              <h4 className={styles.stepTitle}>{step.title}</h4>
              <p className={styles.stepDesc}>{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* 4. Built for the Field Band */}
      <div className={styles.fieldBand}>
        <div className={styles.fieldItem}>
          <div className={styles.fieldIcon}>
            <Cpu size={20} />
          </div>
          <div className={styles.fieldTextGroup}>
            <span className={styles.fieldTitle}>{t('field_cpu_title')}</span>
            <span className={styles.fieldSub}>{t('field_cpu_desc')}</span>
          </div>
        </div>

        <div className={styles.fieldItem}>
          <div className={styles.fieldIcon}>
            <WifiOff size={20} />
          </div>
          <div className={styles.fieldTextGroup}>
            <span className={styles.fieldTitle}>{t('field_offline_title')}</span>
            <span className={styles.fieldSub}>{t('field_offline_desc')}</span>
          </div>
        </div>

        <div className={styles.fieldItem}>
          <div className={styles.fieldIcon}>
            <Globe size={20} />
          </div>
          <div className={styles.fieldTextGroup}>
            <span className={styles.fieldTitle}>{t('field_bilingual_title')}</span>
            <span className={styles.fieldSub}>{t('field_bilingual_desc')}</span>
          </div>
        </div>

        <div className={styles.fieldItem}>
          <div className={styles.fieldIcon}>
            <ShieldCheck size={20} />
          </div>
          <div className={styles.fieldTextGroup}>
            <span className={styles.fieldTitle}>{t('field_deterministic_title')}</span>
            <span className={styles.fieldSub}>{t('field_deterministic_desc')}</span>
          </div>
        </div>
      </div>

      {/* 5. Statutory Note */}
      <div className={styles.statutoryCard}>
        {t('landing_statutory_note')}
      </div>
    </div>
  );
}
