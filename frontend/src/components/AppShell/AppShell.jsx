import React, { useState, useEffect } from 'react';
import { NavLink, useLocation, useNavigate, Outlet } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, User, Play } from 'lucide-react';
import { useT } from '../../i18n/useT';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { LanguageToggle } from '../LanguageToggle/LanguageToggle';
import { StatusDot } from '../StatusDot/StatusDot';
import styles from './AppShell.module.css';

export function AppShell() {
  const { t } = useT();
  const location = useLocation();
  const navigate = useNavigate();
  const reducedMotion = useReducedMotion();

  const [searchQuery, setSearchQuery] = useState('');
  const [officerName, setOfficerName] = useState(() => {
    return localStorage.getItem('nirikshan_officer') || localStorage.getItem('nirikshan_officer_name') || '';
  });

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
          rules_version: data.rules_version || '0.4.0',
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

    const handleStorage = () => {
      const name = localStorage.getItem('nirikshan_officer') || localStorage.getItem('nirikshan_officer_name') || '';
      setOfficerName(name);
    };
    window.addEventListener('storage', handleStorage);
    window.addEventListener('focus', handleStorage);

    return () => {
      clearInterval(interval);
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener('focus', handleStorage);
    };
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/rules?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <div className={styles.shell}>
      {/* 1. Dark Navy Utility Strip */}
      <div className={styles.utilityStrip}>
        <span className={styles.utilityTitle}>{t('utility_strip_title')}</span>
        <div className={styles.utilityRight}>
          <LanguageToggle />
          <StatusDot isOnline={healthInfo.isOnline} showText={true} />
        </div>
      </div>

      {/* Sticky Header Container (Main Header + Second Nav Row) */}
      <div className={styles.headerContainer}>
        {/* 2 & 3. Main Header Row */}
        <div className={styles.headerMain}>
          <NavLink to="/app" className={styles.brandLockup}>
            <img src="/brand/mark-blue.svg" alt="Nirikshan Logo" height="32" />
            <div className={styles.brandTextGroup}>
              <span className={styles.wordmark}>NIRIKSHAN</span>
              <span className={styles.sublabel}>
                {t('sublabel_line1')}
                <br />
                {t('sublabel_line2')}
              </span>
            </div>
          </NavLink>

          <form onSubmit={handleSearchSubmit} className={styles.searchForm}>
            <Search className={styles.searchIcon} size={16} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('search_placeholder')}
              className={styles.searchInput}
            />
          </form>

          <div className={styles.headerActions}>
            <NavLink to="/app" className={styles.startCta}>
              <Play size={14} fill="currentColor" />
              <span>{t('start_inspection')}</span>
            </NavLink>

            <div className={styles.officerChip} title={officerName ? `Inspector: ${officerName}` : 'No officer name set'}>
              <User size={14} />
              <span>{officerName || t('officer_chip_label')}</span>
              {!officerName && <span className={styles.officerBadge}>{t('officer_not_set')}</span>}
            </div>
          </div>
        </div>

        {/* 4. Second Nav Row */}
        <div className={styles.headerNavRow}>
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
              to="/listing"
              className={({ isActive }) => `${styles.navLink} ${isActive ? styles.activeNavLink : ''}`}
            >
              {t('nav_listing')}
            </NavLink>
            <NavLink
              to="/rules"
              className={({ isActive }) => `${styles.navLink} ${isActive ? styles.activeNavLink : ''}`}
            >
              {t('nav_rules')}
            </NavLink>
            {import.meta.env.DEV && (
              <NavLink
                to="/dev/components"
                className={({ isActive }) => `${styles.navLink} ${isActive ? styles.activeNavLink : ''}`}
              >
                {t('nav_dev_components')}
              </NavLink>
            )}
          </nav>

          <span className={styles.navSubtext}>{t('nav_subtext')}</span>
        </div>
      </div>

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

      {/* 5. Rebuilt Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerGrid}>
          <div className={styles.footerCol}>
            <span className={styles.footerColTitle}>{t('footer_col_platform')}</span>
            <div className={styles.footerLinkList}>
              <NavLink to="/app" className={styles.footerLink}>
                {t('nav_app')}
              </NavLink>
              <NavLink to="/review" className={styles.footerLink}>
                {t('nav_review')}
              </NavLink>
              <NavLink to="/listing" className={styles.footerLink}>
                {t('nav_listing')}
              </NavLink>
              <NavLink to="/rules" className={styles.footerLink}>
                {t('nav_rules')}
              </NavLink>
            </div>
          </div>

          <div className={styles.footerCol}>
            <span className={styles.footerColTitle}>{t('footer_col_resources')}</span>
            <div className={styles.footerLinkList}>
              <NavLink to="/rules" className={styles.footerLink}>
                {t('nav_rules')}
              </NavLink>
              <NavLink to="/app" className={styles.footerLink}>
                {t('footer_demo_script')}
              </NavLink>
              <a
                href="https://github.com/rajputjay00/SIH-NIRIKSHAN"
                target="_blank"
                rel="noopener noreferrer"
                className={styles.footerLink}
              >
                {t('footer_github')}
              </a>
            </div>
          </div>

          <div className={styles.footerCol}>
            <span className={styles.footerColTitle}>{t('footer_col_legal')}</span>
            <p className={styles.legalText}>{t('footer_legal_text')}</p>
          </div>
        </div>

        <div className={styles.footerBottom}>
          <div className={styles.footerBottomLeft}>
            <img src="/brand/logo-tricolour.svg" alt="Nirikshan Tricolour Logo" height="20" />
            <span className={styles.psBadge}>{t('footer_ps_id')}</span>
          </div>

          <div className={styles.footerVersion}>
            {healthInfo.rules_version && <span>Rules v{healthInfo.rules_version}</span>}
            {healthInfo.git_sha && <span> &nbsp;|&nbsp; Commit {healthInfo.git_sha}</span>}
          </div>
        </div>
      </footer>
    </div>
  );
}
