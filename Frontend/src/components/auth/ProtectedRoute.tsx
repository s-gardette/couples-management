import React, { useEffect, useState } from 'react';
import { useAuth } from '../../lib/auth-context';
import { AuthModal } from './AuthModal';

interface ProtectedRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  showModal?: boolean;
  redirectTo?: string;
}

export function ProtectedRoute({ 
  children, 
  fallback,
  showModal = true,
  redirectTo 
}: ProtectedRouteProps) {
  const { isAuthenticated, loading } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      if (showModal) {
        setShowAuthModal(true);
      } else if (redirectTo) {
        window.location.href = redirectTo;
      }
    }
  }, [isAuthenticated, loading, showModal, redirectTo]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    if (showModal) {
      return (
        <>
          {fallback || (
            <div className="flex items-center justify-center min-h-screen bg-gray-100">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">
                  Authentication Required
                </h2>
                <p className="text-gray-600 mb-4">
                  Please sign in to access this page.
                </p>
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Sign In
                </button>
              </div>
            </div>
          )}
          <AuthModal
            isOpen={showAuthModal}
            onClose={() => setShowAuthModal(false)}
            onSuccess={() => setShowAuthModal(false)}
          />
        </>
      );
    }

    return fallback || null;
  }

  return <>{children}</>;
} 