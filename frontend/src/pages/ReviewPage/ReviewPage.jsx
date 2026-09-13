import React from 'react';
import { QRPair } from '../../components/QRPair/QRPair';

export function ReviewPage() {
  return (
    <div style={{ textAlign: 'center', padding: '30px 20px' }}>
      <h2>Laptop Review &amp; Session Pairing (/review)</h2>
      <p style={{ color: 'var(--grey-500)', marginBottom: '24px' }}>
        Pair your phone to review real-time label inspections on a larger screen.
      </p>
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <QRPair pairCode="NRK-8421" />
      </div>
    </div>
  );
}
