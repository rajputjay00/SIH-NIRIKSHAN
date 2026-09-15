import React from 'react';
import { motion } from 'framer-motion';
import {
  Camera,
  ScanText,
  Layers,
  ShieldCheck,
  Eye,
  UserCheck,
  FileCheck,
  Check,
} from 'lucide-react';
import { useT } from '../../i18n/useT';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './WorkflowRail.module.css';

const STAGE_DEFINITIONS = [
  {
    id: 'capture',
    icon: Camera,
    labelKey: 'workflow_stage_1_label',
    defaultLabel: 'Capture',
    descKey: 'workflow_stage_1_desc',
    defaultDesc: 'photograph the pack, front and back',
  },
  {
    id: 'read',
    icon: ScanText,
    labelKey: 'workflow_stage_2_label',
    defaultLabel: 'Read the label',
    descKey: 'workflow_stage_2_desc',
    defaultDesc: 'OCR on CPU, text with its position on the image',
  },
  {
    id: 'understand',
    icon: Layers,
    labelKey: 'workflow_stage_3_label',
    defaultLabel: 'Understand the fields',
    descKey: 'workflow_stage_3_desc',
    defaultDesc: 'MRP, net quantity, dates, addresses, pulled out of the text',
  },
  {
    id: 'check',
    icon: ShieldCheck,
    labelKey: 'workflow_stage_4_label',
    defaultLabel: 'Check the rules',
    descKey: 'workflow_stage_4_desc',
    defaultDesc: 'the catalogue runs, exempt rules are marked not applicable',
  },
  {
    id: 'evidence',
    icon: Eye,
    labelKey: 'workflow_stage_5_label',
    defaultLabel: 'Evidence',
    descKey: 'workflow_stage_5_desc',
    defaultDesc: 'every finding points at the box on the image it came from',
  },
  {
    id: 'review',
    icon: UserCheck,
    labelKey: 'workflow_stage_6_label',
    defaultLabel: 'Officer review',
    descKey: 'workflow_stage_6_desc',
    defaultDesc: 'the officer confirms anything the system marks for review',
  },
  {
    id: 'report',
    icon: FileCheck,
    labelKey: 'workflow_stage_7_label',
    defaultLabel: 'Report',
    descKey: 'workflow_stage_7_desc',
    defaultDesc: 'PDF with the image hash, a verification QR and an audit entry',
  },
];

export function WorkflowRail({
  stageStates = [],
  stages = [],
  activeStageIndex = -1,
  compact = false,
  className = '',
}) {
  const { t } = useT();
  const reducedMotion = useReducedMotion();

  const getStageState = (index) => {
    if (stages[index]?.state) return stages[index].state;
    if (stageStates[index]) return stageStates[index];
    if (activeStageIndex >= 0) {
      if (index < activeStageIndex) return 'done';
      if (index === activeStageIndex) return 'active';
      return 'idle';
    }
    return 'idle';
  };

  return (
    <div className={`${styles.railContainer} ${compact ? styles.compactRail : ''} ${className}`}>
      {STAGE_DEFINITIONS.map((def, idx) => {
        const state = getStageState(idx);
        const Icon = def.icon;
        const label = t(def.labelKey) || def.defaultLabel;
        const desc = t(def.descKey) || def.defaultDesc;

        let stateClass = styles.idle;
        if (state === 'active') stateClass = styles.active;
        if (state === 'done') stateClass = styles.done;

        return (
          <React.Fragment key={def.id}>
            <div className={`${styles.stageCard} ${stateClass}`}>
              <div className={styles.stageHeader}>
                <div className={styles.iconBox}>
                  {state === 'done' ? (
                    <Check size={18} className={styles.checkIcon} />
                  ) : (
                    <Icon size={18} />
                  )}
                </div>
                {state === 'active' && !reducedMotion && (
                  <motion.div
                    className={styles.activePulseBadge}
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
                  />
                )}
              </div>
              <h4 className={styles.stageLabel}>{label}</h4>
              <p className={styles.stageDesc}>{desc}</p>
            </div>

            {idx < STAGE_DEFINITIONS.length - 1 && (
              <div
                className={`${styles.connector} ${
                  state === 'done' && getStageState(idx + 1) !== 'idle'
                    ? styles.connectorDone
                    : ''
                }`}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
