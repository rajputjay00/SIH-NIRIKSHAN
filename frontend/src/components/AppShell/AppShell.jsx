import React, { useState, useEffect } from 'react';
import { NavLink, useLocation, Outlet } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useT } from '../../i18n/useT';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { LanguageToggle } from '../LanguageToggle/LanguageToggle';
import { StatusDot } from '../StatusDot/StatusDot';
import styles from './AppShell.module.css';

export function AppShell() {
  const { t } = useT();
  const location = useLocation();
  const reducedMotion = useReducedMotion();

  const [healthInfo, setHealthInfo] = useState({
    status: 'checking',
    isOnline: false,
    rules_version: null,
    git_sha: null,
  });

  const checkHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setHealthInfo({
          status: 'online',
          isOnline: true,
          rules_version: data.rules_version || '2026.1',
          git_sha: data.git_sha || 'head',
        });
      } else {
        setHealthInfo((prev) => ({ ...prev, status: 'offline', isOnline: false }));
      }
    } catch (err) {
      setHealthInfo((prev) => ({ ...prev, status: 'offline', isOnline: false }));
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={styles.shell}>
      {/* Header */}
      <header className={styles.header}>
        <NavLink to="/app" className={styles.brandLink}>
          <img src="/brand/mark-blue.svg" alt="Nirikshan Logo" height="32" />
          <span>Nirikshan</span>
        </NavLink>

        <nav className={styles.nav}>
          <NavLink
            to="/app"
            className={({ isActive }) => `${styles.navLink} ${isActive ? styles.activeNavLink : ''}`}
          >
            {t('nav_app')}
          </NavLink>
          <NavLink
            to="/review"
            className={({ isActive }) => `${styles.navLink} ${isActive ? styles.activeNavLink : ''}`}
          >
            {t('nav_review')}
          </NavLink>
          <NavLink
            to="/rules"
            className={({ isActive }) => `${styles.navLink} ${isActive ? styles.activeNavLink : ''}`}
          >
            {t('nav_rules')}
          </NavLink>
        </nav>

        <div className={styles.headerRight}>
          <LanguageToggle />
          <StatusDot isOnline={healthInfo.isOnline} />
        </div>
      </header>

      {/* Main Content with Route Transition Curtain Wipe */}
      <main className={styles.mainContent}>
        <AnimatePresence mode="wait">
          {!reducedMotion && (
            <motion.div
              key={location.pathname}
              className={styles.curtainOverlay}
              initial={{ x: '-100%' }}
              animate={{ x: '100%' }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            />
          )}
        </AnimatePresence>

        <Outlet />
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerLeft}>
          <img src="/brand/logo-tricolour.svg" alt="Nirikshan Tricolour Logo" height="24" />
          <span>{t('footer_tagline')}</span>
        </div>

        <div className={styles.footerRight}>
          {healthInfo.rules_version && <span>Rules v{healthInfo.rules_version}</span>}
          {healthInfo.git_sha && <span> &nbsp;|&nbsp; Commit {healthInfo.git_sha}</span>}
        </div>
      </footer>
    </div>
  );
}
