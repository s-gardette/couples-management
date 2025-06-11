import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export function LogoutHandler() {
  const [status, setStatus] = useState<'idle' | 'logging-out' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleLogout = async () => {
    setStatus('logging-out');
    setMessage('Signing you out...');

    try {
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      const result = await response.json();

      if (response.ok) {
        setStatus('success');
        setMessage('You have been successfully logged out.');
        
        // Redirect to home page after a short delay
        setTimeout(() => {
          window.location.href = '/';
        }, 2000);
      } else {
        setStatus('error');
        setMessage(result.message || 'Logout failed. Please try again.');
      }
    } catch (error) {
      setStatus('error');
      setMessage('Network error. Please check your connection and try again.');
      console.error('Logout error:', error);
    }
  };

  // Auto-logout when component mounts if user confirms
  useEffect(() => {
    // Optional: Auto-logout without confirmation
    // handleLogout();
  }, []);

  const getStatusIcon = () => {
    switch (status) {
      case 'logging-out':
        return (
          <svg
            className="animate-spin h-8 w-8 text-blue-600 mx-auto"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        );
      case 'success':
        return (
          <svg
            className="h-8 w-8 text-green-600 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        );
      case 'error':
        return (
          <svg
            className="h-8 w-8 text-red-600 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        );
      default:
        return (
          <svg
            className="h-8 w-8 text-gray-600 mx-auto"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
            />
          </svg>
        );
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Sign Out</CardTitle>
        <CardDescription>
          {status === 'idle' 
            ? 'Are you sure you want to sign out?'
            : message
          }
        </CardDescription>
      </CardHeader>
      <CardContent className="text-center space-y-6">
        {getStatusIcon()}
        
        {status === 'idle' && (
          <div className="space-y-4">
            <Button 
              onClick={handleLogout} 
              className="w-full"
              variant="destructive"
            >
              Yes, Sign Out
            </Button>
            <Button 
              variant="outline" 
              className="w-full"
              asChild
            >
              <a href="/dashboard">Cancel</a>
            </Button>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-4">
            <Button 
              onClick={handleLogout} 
              className="w-full"
              variant="destructive"
            >
              Try Again
            </Button>
            <Button 
              variant="outline" 
              className="w-full"
              asChild
            >
              <a href="/dashboard">Cancel</a>
            </Button>
          </div>
        )}

        {status === 'success' && (
          <p className="text-sm text-muted-foreground">
            Redirecting to home page...
          </p>
        )}

        {status === 'logging-out' && (
          <p className="text-sm text-muted-foreground">
            Please wait while we sign you out securely.
          </p>
        )}
      </CardContent>
    </Card>
  );
} 