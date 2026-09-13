import React from 'react';
import { motion } from 'framer-motion';
import { useT } from '../../i18n/useT';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './LanguageToggle.module.css';

export function LanguageToggle({ className = '' }) {
  const { lang, setLang } = useT();
  const reducedMotion = useReducedMotion();

  const toggleLanguage = () => {
    setLang(lang === 'en' ? 'hi' : 'en');
  };

  return (
    <motion.button
      type="button"
      onClick={toggleLanguage}
      className={`${styles.toggleBtn} ${className}`}
      whileTap={reducedMotion ? {} : { scale: 0.94 }}
    >
      <motion.span
        key={lang}
        initial={reducedMotion ? { opacity: 1 } : { opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
      >
        {lang === 'en' ? 'EN' : 'हिं'}
      </motion.span>
    </motion.button>
  );
}
