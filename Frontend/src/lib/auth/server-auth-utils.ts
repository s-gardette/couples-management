// Server-side authentication utilities for Astro pages
import type { APIContext } from 'astro';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export interface ServerUser {
  id: string;
  email: string;
  username: string;
  first_name?: string;
  last_name?: string;
  avatar_url?: string;
  email_verified: boolean;
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Check if user is authenticated by verifying the access token with the backend
 * Returns user data if authenticated, null if not
 */
export async function getAuthenticatedUser(cookies: APIContext['cookies']): Promise<ServerUser | null> {
  try {
    const accessToken = cookies.get('access_token')?.value;
    
    if (!accessToken) {
      return null;
    }

    // Verify token with backend
    const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      // If token is invalid, we should clear the cookies
      if (response.status === 401) {
        cookies.delete('access_token', { path: '/' });
        cookies.delete('refresh_token', { path: '/' });
      }
      return null;
    }

    const userData = await response.json();
    return userData;

  } catch (error) {
    console.error('Auth check error:', error);
    return null;
  }
}

/**
 * Check if user is authenticated, returns true/false
 */
export async function isLoggedIn(cookies: APIContext['cookies']): Promise<boolean> {
  const user = await getAuthenticatedUser(cookies);
  return !!user;
}

/**
 * Require authentication - redirects to login if not authenticated
 * Returns user data if authenticated, or throws redirect response
 */
export async function requireAuth(
  context: APIContext,
  redirectTo: string = '/auth/signin'
): Promise<ServerUser> {
  const user = await getAuthenticatedUser(context.cookies);
  
  if (!user) {
    throw context.redirect(redirectTo);
  }
  
  return user;
}

/**
 * Redirect authenticated users (useful for login/signup pages)
 * Returns null if not authenticated, or throws redirect response if authenticated
 */
export async function redirectIfAuthenticated(
  context: APIContext,
  redirectTo: string = '/dashboard'
): Promise<null> {
  const user = await getAuthenticatedUser(context.cookies);
  
  if (user) {
    throw context.redirect(redirectTo);
  }
  
  return null;
} 