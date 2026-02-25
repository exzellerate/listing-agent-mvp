import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ClerkProvider, SignIn, SignUp, UserProfile } from '@clerk/clerk-react'
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
import LandingPage from './pages/LandingPage.tsx'
import ProtectedRoute from './components/ProtectedRoute.tsx'
import AuthProvider from './components/AuthProvider.tsx'

// Get Clerk publishable key from environment
const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!CLERK_PUBLISHABLE_KEY) {
  throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY environment variable')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/sign-in/*" element={<SignIn routing="path" path="/sign-in" fallbackRedirectUrl="/upload" />} />
            <Route path="/sign-up/*" element={<SignUp routing="path" path="/sign-up" fallbackRedirectUrl="/upload" />} />

            {/* Protected routes - require authentication */}
            <Route element={<ProtectedRoute />}>
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/listings" element={<ListingsPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/testing" element={<TestingPage />} />
              <Route path="/connections" element={<ConnectionsPage />} />
              <Route path="/drafts" element={<DraftsPage />} />
              <Route path="/feedback" element={<FeedbackPage />} />
              <Route path="/profile/*" element={<UserProfile routing="path" path="/profile" />} />
              <Route path="/ebay/callback" element={<EbayCallback />} />
              <Route path="/old" element={<App />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ClerkProvider>
  </StrictMode>,
)
