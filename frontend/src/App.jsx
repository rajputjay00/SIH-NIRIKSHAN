import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/AppShell/AppShell';

const LandingPage = lazy(() => import('./pages/LandingPage/LandingPage').then(m => ({ default: m.LandingPage })));
const AppPage = lazy(() => import('./pages/AppPage/AppPage').then(m => ({ default: m.AppPage })));
const ReviewPage = lazy(() => import('./pages/ReviewPage/ReviewPage').then(m => ({ default: m.ReviewPage })));
const RulesPage = lazy(() => import('./pages/RulesPage/RulesPage').then(m => ({ default: m.RulesPage })));
const DevComponents = lazy(() => import('./pages/DevComponents/DevComponents').then(m => ({ default: m.DevComponents })));

function PageLoader() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '300px', color: 'var(--blue-500)' }}>
      Loading Nirikshan...
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<AppShell />}>
            <Route index element={<LandingPage />} />
            <Route path="app" element={<AppPage />} />
            <Route path="review" element={<ReviewPage />} />
            <Route path="rules" element={<RulesPage />} />
            {import.meta.env.DEV && <Route path="dev/components" element={<DevComponents />} />}
            <Route path="*" element={<Navigate to="/app" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

