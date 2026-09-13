import React from 'react';
import { NavLink } from 'react-router-dom';
import { Button } from '../../components/Button/Button';
import { Logo } from '../../components/Logo/Logo';

export function LandingPage() {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px' }}>
      <Logo size={80} animate={true} variant="tricolour" />
      <h1 style={{ marginTop: '20px', color: 'var(--navy-900)' }}>Nirikshan</h1>
      <p style={{ color: 'var(--grey-500)', fontSize: '1.1rem', maxWidth: '600px', margin: '12px auto' }}>
        Rules-as-code compliance for every package under Legal Metrology (Packaged Commodities) Rules, 2011.
      </p>
      <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', marginTop: '24px' }}>
        <NavLink to="/app">
          <Button variant="primary">Start Inspection</Button>
        </NavLink>
        <NavLink to="/rules">
          <Button variant="secondary">Explore Rules</Button>
        </NavLink>
      </div>
    </div>
  );
}
