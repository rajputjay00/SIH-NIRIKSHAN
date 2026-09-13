import React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './Button.module.css';

export function Button({
  children,
  variant = 'primary',
  disabled = false,
  onClick,
  className = '',
  type = 'button',
  icon: Icon,
  ...props
}) {
  const reducedMotion = useReducedMotion();

  const motionProps = reducedMotion || disabled
    ? {}
    : {
        whileHover: { y: -1 },
        whileTap: { scale: 0.97 },
      };

  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${styles.button} ${styles[variant]} ${disabled ? styles.disabled : ''} ${className}`}
      {...motionProps}
      {...props}
    >
      {Icon && <Icon size={18} />}
      <span>{children}</span>
    </motion.button>
  );
}
