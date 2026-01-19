import { useEffect } from 'react';
import { useAuth } from '@clerk/clerk-react';
import { setAuthTokenGetter } from '../services/api';

/**
 * AuthProvider component that sets up the API service with Clerk's auth token.
 * This should be rendered inside ClerkProvider and wraps the app content.
 */
export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { getToken } = useAuth();

  useEffect(() => {
    // Set the token getter function that the API service will use
    setAuthTokenGetter(async () => {
      try {
        return await getToken();
      } catch (error) {
        console.error('Failed to get Clerk token:', error);
        return null;
      }
    });
  }, [getToken]);

  return <>{children}</>;
}
