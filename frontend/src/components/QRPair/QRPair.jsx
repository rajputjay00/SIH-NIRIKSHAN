import React from 'react';
import { QRCodeSVG } from 'qrcode.react';
import styles from './QRPair.module.css';

export function QRPair({ pairCode = 'NRK-8421', url = 'https://nirikshan.app/pair/NRK-8421', className = '' }) {
  return (
    <div className={`${styles.qrCard} ${className}`}>
      <QRCodeSVG value={url} size={160} fgColor="var(--navy-900)" bgColor="#FFFFFF" />
      <div className={styles.codeBox}>{pairCode}</div>
      <div className={styles.hintText}>Scan with phone camera to pair live inspection session</div>
    </div>
  );
}
