import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function EbayCallback() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Processing eBay authorization...');

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');

      // Check for OAuth 1.0a parameters (old format)
      const ebaytkn = searchParams.get('ebaytkn');
      const username = searchParams.get('username');

      // Handle error from eBay
      if (error) {
        setStatus('error');
        setMessage(`Authorization failed: ${error}`);
        setTimeout(() => {
          window.close();
        }, 3000);
        return;
      }

      // Check if this is OAuth 1.0a callback (wrong type)
      if (ebaytkn || username) {
        setStatus('error');
        setMessage('OAuth 1.0a callback detected. Please configure your RuName for OAuth 2.0 (Authorization Code Grant) in the eBay Developer Portal, not OAuth 1.0a (Sign In).');
        // Don't auto-close so user can read the message
        return;
      }

      // Validate we have a code
      if (!code) {
        setStatus('error');
        setMessage('No authorization code received. Expected OAuth 2.0 callback with "code" parameter.');
        setTimeout(() => {
          window.close();
        }, 5000);
        return;
      }

      try {
        // Exchange code for token
        const formData = new FormData();
        formData.append('code', code);
        if (state) {
          formData.append('state', state);
        }

        const response = await fetch(`${API_BASE_URL}/api/ebay/auth/callback`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to exchange authorization code');
        }

        await response.json();

        setStatus('success');
        setMessage('Successfully connected to eBay! You can close this window.');

        // Close the window after 2 seconds
        setTimeout(() => {
          window.close();
          // If window.close() doesn't work (some browsers prevent it), redirect to main app
          if (!window.closed) {
            window.location.href = '/';
          }
        }, 2000);
      } catch (err: any) {
        console.error('Callback error:', err);
        setStatus('error');
        setMessage(err.message || 'Failed to complete authorization');

        setTimeout(() => {
          window.close();
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <div className="mx-auto w-16 h-16 mb-4">
                <svg className="animate-spin h-16 w-16 text-blue-600" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Processing...</h2>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="mx-auto w-16 h-16 mb-4 bg-green-100 rounded-full flex items-center justify-center">
                <svg className="w-10 h-10 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-green-900 mb-2">Success!</h2>
            </>
          )}

          {status === 'error' && (
            <>
              <div className="mx-auto w-16 h-16 mb-4 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-10 h-10 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-red-900 mb-2">Error</h2>
            </>
          )}

          <p className="text-gray-700">{message}</p>

          {status !== 'processing' && (
            <button
              onClick={() => window.close()}
              className="mt-6 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Close Window
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
