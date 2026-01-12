import { useState, useEffect } from 'react';
import type { AnalysisResult, PricingData } from '../types';
import EbayListingWizard from './EbayListingWizard';

interface EbayPostingSectionProps {
  result: AnalysisResult;
  pricingData?: PricingData;
  analysisId?: number;
  imageFiles?: File[];
}

interface EbayAuthStatus {
  authenticated: boolean;
  expires_at?: string;
  expired?: boolean;
  environment?: string;
  is_production?: boolean;
}

interface EbayListingStatus {
  success: boolean;
  listing_id?: number;
  sku?: string;
  status?: string;
  message?: string;
  ebay_url?: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function EbayPostingSection({ result, pricingData, analysisId, imageFiles = [] }: EbayPostingSectionProps) {
  const [authStatus, setAuthStatus] = useState<EbayAuthStatus | null>(null);
  const [loadingAuth, setLoadingAuth] = useState(true);
  const [listingStatus, setListingStatus] = useState<EbayListingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [imageUrls, setImageUrls] = useState<string[]>([]);

  // Check eBay authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  // Convert image files to URLs
  useEffect(() => {
    if (imageFiles && imageFiles.length > 0) {
      const urls = imageFiles.map(file => URL.createObjectURL(file));
      setImageUrls(urls);

      // Cleanup function to revoke object URLs
      return () => {
        urls.forEach(url => URL.revokeObjectURL(url));
      };
    }
  }, [imageFiles]);

  const checkAuthStatus = async () => {
    try {
      setLoadingAuth(true);
      const response = await fetch(`${API_BASE_URL}/api/ebay/auth/status`);

      if (!response.ok) {
        throw new Error('Failed to check authentication status');
      }

      const data = await response.json();
      setAuthStatus(data);
    } catch (err) {
      console.error('Auth status check failed:', err);
      setAuthStatus({ authenticated: false });
    } finally {
      setLoadingAuth(false);
    }
  };

  const handleAuthenticate = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/ebay/auth/url`);

      if (!response.ok) {
        throw new Error('Failed to get authorization URL');
      }

      const data = await response.json();

      // Open eBay OAuth page in new window
      const authWindow = window.open(data.authorization_url, '_blank', 'width=600,height=700');

      if (!authWindow || authWindow.closed || typeof authWindow.closed === 'undefined') {
        // Popup was blocked - show the URL to the user
        const confirmed = confirm(
          'Popup was blocked by your browser.\n\n' +
          'Click OK to open the eBay authorization page in a new tab, ' +
          'or check your popup blocker settings.\n\n' +
          'After authorizing, click "Check Status" to refresh.'
        );

        if (confirmed) {
          window.location.href = data.authorization_url;
        }
      } else {
        // Show message to user
        alert('Please complete eBay authorization in the new window, then click "Check Status" to refresh.');
      }
    } catch (err) {
      console.error('Failed to get auth URL:', err);
      setError('Failed to start eBay authentication');
    }
  };

  const handleDisconnect = async () => {
    const confirmed = confirm('Are you sure you want to disconnect your eBay account?');
    if (!confirmed) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/ebay/auth/revoke`, {
        method: 'POST',
      });

      if (!response.ok) {
        throw new Error('Failed to disconnect eBay account');
      }

      // Update auth status
      setAuthStatus({ authenticated: false });
      setError(null);
      setListingStatus(null);
    } catch (err) {
      console.error('Failed to disconnect:', err);
      setError('Failed to disconnect eBay account');
    }
  };

  if (loadingAuth) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-2xl font-semibold mb-4 text-gray-800">Post to eBay</h2>
        <p className="text-gray-600">Checking eBay connection...</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-semibold text-gray-800">Post to eBay</h2>
        {/* Environment Badge */}
        {authStatus?.environment && (
          <div className={`px-4 py-2 rounded-lg font-bold text-sm border-2 ${
            authStatus.is_production
              ? 'bg-red-50 border-red-500 text-red-700'
              : 'bg-yellow-50 border-yellow-500 text-yellow-700'
          }`}>
            {authStatus.is_production ? '🔴 PRODUCTION MODE' : '🟡 SANDBOX MODE'}
          </div>
        )}
      </div>

      {/* Production Warning */}
      {authStatus?.is_production && authStatus?.authenticated && (
        <div className="mb-4 bg-red-50 border-2 border-red-300 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <svg className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div>
              <h4 className="font-bold text-red-900">Warning: Production Environment</h4>
              <p className="text-sm text-red-800 mt-1">
                Listings created in this mode will be LIVE on eBay and will incur actual listing fees. Make sure all information is accurate before posting.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Authentication Status */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            {authStatus?.authenticated && !authStatus?.expired ? (
              <>
                <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span className="font-medium text-green-600">Connected to eBay</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="font-medium text-amber-600">Not connected to eBay</span>
              </>
            )}
          </div>
          <button
            onClick={checkAuthStatus}
            className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm"
          >
            Check Status
          </button>
        </div>

        {/* Not connected message with link to connections page */}
        {!authStatus?.authenticated && (
          <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              Connect your eBay account to post listings directly from the Listing Agent.
              You can manage all your platform connections from the{' '}
              <a href="/connections" className="font-semibold text-blue-600 hover:text-blue-800 underline">
                Connections page
              </a>
              .
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleAuthenticate}
            disabled={authStatus?.authenticated && !authStatus?.expired}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              authStatus?.authenticated && !authStatus?.expired
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            Connect eBay Account
          </button>
          <button
            onClick={handleDisconnect}
            disabled={!authStatus?.authenticated}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              !authStatus?.authenticated
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-red-600 text-white hover:bg-red-700'
            }`}
          >
            Disconnect
          </button>
        </div>
      </div>

      {/* Posting Section */}
      {authStatus?.authenticated && !authStatus?.expired && (
        <div className="space-y-4">
          {/* Listing Preview */}
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
            <h3 className="font-semibold text-gray-800 mb-2">Listing Preview</h3>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium text-gray-700">Title:</span>
                <p className="text-gray-600 mt-1">{result.suggested_title}</p>
              </div>
              <div>
                <span className="font-medium text-gray-700">Price:</span>
                <p className="text-gray-600 mt-1">
                  ${pricingData?.statistics?.suggested_price?.toFixed(2) || '50.00'}
                </p>
              </div>
              <div>
                <span className="font-medium text-gray-700">Condition:</span>
                <p className="text-gray-600 mt-1">{result.condition || 'Used - Excellent'}</p>
              </div>
            </div>
          </div>

          {/* Post Button */}
          <button
            onClick={() => setWizardOpen(true)}
            className="w-full px-6 py-3 rounded-lg font-medium transition-colors bg-green-600 hover:bg-green-700 text-white"
          >
            Create eBay Listing
          </button>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center gap-2 text-red-800">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <span className="font-medium">{error}</span>
              </div>
            </div>
          )}

          {/* Success/Status Message */}
          {listingStatus && (
            <div className={`border rounded-lg p-4 ${
              listingStatus.status === 'published'
                ? 'bg-green-50 border-green-200'
                : listingStatus.status === 'failed'
                ? 'bg-red-50 border-red-200'
                : 'bg-blue-50 border-blue-200'
            }`}>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {listingStatus.status === 'published' ? (
                    <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  ) : listingStatus.status === 'failed' ? (
                    <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="animate-spin h-5 w-5 text-blue-600" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  )}
                  <span className={`font-medium ${
                    listingStatus.status === 'published'
                      ? 'text-green-800'
                      : listingStatus.status === 'failed'
                      ? 'text-red-800'
                      : 'text-blue-800'
                  }`}>
                    {listingStatus.status === 'published'
                      ? 'Successfully posted to eBay!'
                      : listingStatus.status === 'failed'
                      ? 'Failed to post listing'
                      : 'Processing...'}
                  </span>
                </div>

                {listingStatus.message && (
                  <p className="text-sm text-gray-700">{listingStatus.message}</p>
                )}

                {listingStatus.sku && (
                  <p className="text-sm text-gray-600">SKU: {listingStatus.sku}</p>
                )}

                {listingStatus.status && (
                  <p className="text-sm text-gray-600">
                    Status: {listingStatus.status.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                  </p>
                )}

                {listingStatus.ebay_url && (
                  <a
                    href={listingStatus.ebay_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 font-medium"
                  >
                    View on eBay
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
                      <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
                    </svg>
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Wizard */}
      <EbayListingWizard
        isOpen={wizardOpen}
        onClose={() => setWizardOpen(false)}
        productData={{
          title: result.suggested_title,
          description: result.suggested_description,
          images: imageUrls,
          price: pricingData?.statistics?.suggested_price || 50.0,
          condition: result.condition || 'USED_EXCELLENT',
          // AI-generated product data for category recommendations
          product_name: result.product_name,
          brand: result.brand,
          category: result.category,
          ebay_category_keywords: result.ebay_category_keywords
        }}
        analysisId={analysisId}
        ebayCategory={result.ebay_category}
        ebayAspects={result.ebay_aspects}
        onSuccess={(listingId) => {
          setWizardOpen(false);
          setListingStatus({
            success: true,
            listing_id: parseInt(listingId),
            status: 'published',
            message: 'Listing created successfully!'
          });
        }}
      />
    </div>
  );
}
