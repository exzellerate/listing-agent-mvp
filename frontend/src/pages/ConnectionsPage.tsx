import { useState, useEffect } from 'react';
import { Platform } from '../types';

interface ConnectionStatus {
  platform: Platform;
  label: string;
  icon: string;
  authenticated: boolean;
  loading: boolean;
  expires_at?: string;
  expired?: boolean;
  gradient: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ConnectionsPage() {
  const [connections, setConnections] = useState<ConnectionStatus[]>([
    { platform: 'ebay', label: 'eBay', icon: '🏷️', authenticated: false, loading: true, gradient: 'from-yellow-400 to-yellow-600' },
    { platform: 'amazon', label: 'Amazon', icon: '📦', authenticated: false, loading: true, gradient: 'from-orange-400 to-orange-600' },
    { platform: 'walmart', label: 'Walmart', icon: '🛒', authenticated: false, loading: true, gradient: 'from-blue-400 to-blue-600' },
  ]);

  useEffect(() => {
    checkAllConnections();
  }, []);

  const checkAllConnections = async () => {
    // Check eBay connection
    checkEbayConnection();

    // For now, Amazon and Walmart are marked as not authenticated
    // These will be implemented in the future
    setConnections(prev => prev.map(conn => {
      if (conn.platform !== 'ebay') {
        return { ...conn, loading: false, authenticated: false };
      }
      return conn;
    }));
  };

  const checkEbayConnection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/ebay/auth/status`);
      if (response.ok) {
        const data = await response.json();
        setConnections(prev => prev.map(conn =>
          conn.platform === 'ebay'
            ? { ...conn, authenticated: data.authenticated, expires_at: data.expires_at, expired: data.expired, loading: false }
            : conn
        ));
      } else {
        setConnections(prev => prev.map(conn =>
          conn.platform === 'ebay' ? { ...conn, loading: false, authenticated: false } : conn
        ));
      }
    } catch (error) {
      console.error('Failed to check eBay connection:', error);
      setConnections(prev => prev.map(conn =>
        conn.platform === 'ebay' ? { ...conn, loading: false, authenticated: false } : conn
      ));
    }
  };

  const handleConnect = async (platform: Platform) => {
    if (platform === 'ebay') {
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
            'After authorizing, click "Refresh Status" to update your connection.'
          );

          if (confirmed) {
            window.location.href = data.authorization_url;
          }
        } else {
          // Poll for authentication completion
          const pollInterval = setInterval(async () => {
            if (authWindow.closed) {
              clearInterval(pollInterval);
              await checkEbayConnection();
            }
          }, 1000);
        }
      } catch (error) {
        console.error('Failed to initiate eBay authentication:', error);
        alert('Failed to connect to eBay. Please try again.');
      }
    } else {
      alert(`${platform.charAt(0).toUpperCase() + platform.slice(1)} integration coming soon!`);
    }
  };

  const handleDisconnect = async (platform: Platform) => {
    if (platform === 'ebay') {
      if (!confirm('Are you sure you want to disconnect from eBay? You will need to re-authorize to post listings.')) {
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/ebay/auth/revoke`, { method: 'POST' });
        if (response.ok) {
          await checkEbayConnection();
        } else {
          alert('Failed to disconnect from eBay. Please try again.');
        }
      } catch (error) {
        console.error('Failed to disconnect from eBay:', error);
        alert('Failed to disconnect from eBay. Please try again.');
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm shadow-sm border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                Platform Connections
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                Connect your marketplace accounts to enable listing creation
              </p>
            </div>
            <a
              href="/"
              className="px-4 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg font-medium transition-colors"
            >
              ← Back to exzellerate
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 p-8">
          <div className="space-y-6">
            {connections.filter(c => c.platform === 'ebay').map((connection) => (
              <div
                key={connection.platform}
                className="border-2 border-gray-200 rounded-xl p-6 hover:border-gray-300 transition-all duration-300 hover:shadow-lg"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${connection.gradient} flex items-center justify-center text-3xl shadow-lg`}>
                      {connection.icon}
                    </div>
                    <div>
                      <h3 className="text-2xl font-bold text-gray-800">{connection.label}</h3>
                      <div className="mt-1 flex items-center gap-2">
                        {connection.loading ? (
                          <span className="text-sm text-gray-500">Checking status...</span>
                        ) : connection.authenticated ? (
                          <>
                            <div className="flex items-center gap-1">
                              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                              <span className="text-sm font-medium text-green-600">Connected</span>
                            </div>
                            {connection.expires_at && (
                              <span className="text-xs text-gray-500">
                                • Expires {new Date(connection.expires_at).toLocaleDateString()}
                              </span>
                            )}
                            {connection.expired && (
                              <span className="text-xs text-orange-600 font-medium">
                                (Token Expired - Reconnect Required)
                              </span>
                            )}
                          </>
                        ) : (
                          <div className="flex items-center gap-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                            <span className="text-sm text-gray-500">Not connected</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-3">
                    {connection.authenticated && !connection.loading ? (
                      <>
                        <button
                          onClick={() => handleDisconnect(connection.platform)}
                          className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg font-medium transition-colors"
                        >
                          Disconnect
                        </button>
                        <button
                          onClick={() => connection.platform === 'ebay' ? checkEbayConnection() : null}
                          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors"
                        >
                          Refresh Status
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleConnect(connection.platform)}
                        disabled={connection.loading}
                        className={`px-6 py-3 bg-gradient-to-r ${connection.gradient} hover:opacity-90 text-white rounded-lg font-bold transition-all duration-300 transform hover:scale-105 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
                      >
                        {connection.loading ? 'Checking...' : 'Connect'}
                      </button>
                    )}
                  </div>
                </div>

                {/* Platform-specific information */}
                {connection.platform === 'ebay' && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-600">
                      Connect your eBay account to create and manage listings directly from exzellerate.
                    </p>
                  </div>
                )}

                {connection.platform === 'amazon' && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-600">
                      Amazon integration coming soon. Connect to create listings on Amazon Marketplace.
                    </p>
                  </div>
                )}

                {connection.platform === 'walmart' && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm text-gray-600">
                      Walmart integration coming soon. Connect to create listings on Walmart Marketplace.
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Info Box */}
        <div className="mt-8 bg-blue-50 border-2 border-blue-200 rounded-xl p-6">
          <div className="flex gap-4">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
            <div>
              <h4 className="font-bold text-blue-900 mb-2">About Platform Connections</h4>
              <p className="text-sm text-blue-800">
                Connecting your marketplace accounts allows you to create listings directly from exzellerate.
                Your credentials are securely stored and you can disconnect at any time. Once connected, you can
                analyze product images and post listings without needing to manually enter marketplace details.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
