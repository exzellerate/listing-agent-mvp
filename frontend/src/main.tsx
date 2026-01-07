import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import UploadPage from './pages/UploadPage.tsx'
import ListingsPage from './pages/ListingsPage.tsx'
import AnalyticsPage from './pages/AnalyticsPage.tsx'
import SettingsPage from './pages/SettingsPage.tsx'
import TestingPage from './pages/TestingPage.tsx'
import EbayCallback from './pages/EbayCallback.tsx'
import ConnectionsPage from './pages/ConnectionsPage.tsx'
import DraftsPage from './pages/DraftsPage.tsx'
import FeedbackPage from './pages/FeedbackPage.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/listings" element={<ListingsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/testing" element={<TestingPage />} />
        <Route path="/connections" element={<ConnectionsPage />} />
        <Route path="/drafts" element={<DraftsPage />} />
        <Route path="/feedback" element={<FeedbackPage />} />
        <Route path="/ebay/callback" element={<EbayCallback />} />
        <Route path="/old" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
