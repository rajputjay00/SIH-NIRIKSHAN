import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppShell } from './components/AppShell/AppShell';
import { LandingPage } from './pages/LandingPage/LandingPage';
import { AppPage } from './pages/AppPage/AppPage';
import { ReviewPage } from './pages/ReviewPage/ReviewPage';
import { RulesPage } from './pages/RulesPage/RulesPage';
import { DevComponents } from './pages/DevComponents/DevComponents';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppShell />}>
          <Route index element={<LandingPage />} />
          <Route path="app" element={<AppPage />} />
          <Route path="review" element={<ReviewPage />} />
          <Route path="rules" element={<RulesPage />} />
          <Route path="dev/components" element={<DevComponents />} />
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
