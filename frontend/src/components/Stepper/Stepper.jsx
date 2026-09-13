import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Cpu, CheckCircle } from 'lucide-react';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useT } from '../../i18n/useT';
import styles from './Stepper.module.css';

export function Stepper({ activeStep = 1, className = '' }) {
  const { t } = useT();
  const reducedMotion = useReducedMotion();

  const steps = [
    { id: 1, label: t('stepper_reading_text'), icon: FileText },
    { id: 2, label: t('stepper_understanding_declarations'), icon: Cpu },
    { id: 3, label: t('stepper_checking_rules'), icon: CheckCircle },
  ];

  return (
    <div className={`${styles.stepperContainer} ${className}`}>
      {steps.map((step) => {
        const Icon = step.icon;
        const isCompleted = activeStep > step.id;
        const isActive = activeStep === step.id;

        let statusClass = '';
        if (isCompleted) statusClass = styles.completed;
        else if (isActive) statusClass = styles.active;

        return (
          <div key={step.id} className={`${styles.stepItem} ${statusClass}`}>
            <motion.div
              className={styles.iconCircle}
              animate={isActive && !reducedMotion ? { scale: [1, 1.1, 1] } : {}}
              transition={{ repeat: Infinity, duration: 1.5 }}
            >
              <Icon size={18} />
            </motion.div>
            <span className={styles.stepLabel}>{step.label}</span>
          </div>
        );
      })}
    </div>
  );
}
