import type { JSX } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import FloatDashboard from '../components/float/FloatDashboard';

export default function MainRoutes(): JSX.Element {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<FloatDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
