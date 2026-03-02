import { useAuth } from '@clerk/clerk-react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

/**
 * ProtectedRoute component that wraps routes requiring authentication.
 * Redirects unauthenticated users to the sign-in page.
 */
export default function ProtectedRoute() {
  const { isLoaded, isSignedIn } = useAuth();
  const location = useLocation();

  // Show loading state while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to home if not authenticated
  if (!isSignedIn) {
    return <Navigate to="/" replace />;
  }

  // Render the protected content
  return <Outlet />;
}
