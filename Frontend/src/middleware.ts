import { defineMiddleware } from 'astro:middleware';
import { getAuthenticatedUser } from './lib/auth/server-auth-utils';

// Define which routes require authentication
const protectedRoutes = [
  '/dashboard',
  '/profile',
  '/settings',
  '/expenses',
  '/budgets',
  // Add any other routes that need protection
];

// Define which routes should redirect authenticated users
const guestOnlyRoutes = [
  '/auth/signin',
  '/auth/signup', 
  '/auth/login',
  '/auth/register',
];

export const onRequest = defineMiddleware(async (context, next) => {
  const { url, cookies, redirect } = context;
  const pathname = url.pathname;

  // Skip auth checks for API routes (they handle their own auth)
  if (pathname.startsWith('/api/')) {
    return next();
  }

  // Check if this is a protected route
  const isProtectedRoute = protectedRoutes.some(route => 
    pathname.startsWith(route)
  );

  // Check if this is a guest-only route
  const isGuestOnlyRoute = guestOnlyRoutes.some(route => 
    pathname.startsWith(route)
  );

  if (isProtectedRoute || isGuestOnlyRoute) {
    const user = await getAuthenticatedUser(cookies);
    const isAuthenticated = !!user;

    // Redirect unauthenticated users from protected routes
    if (isProtectedRoute && !isAuthenticated) {
      return redirect('/auth/signin');
    }

    // Redirect authenticated users from guest-only routes
    if (isGuestOnlyRoute && isAuthenticated) {
      return redirect('/dashboard');
    }
  }

  return next();
}); 