# Authentication Protection Guide

This guide shows you how to protect pages in your Astro application using server-side authentication checks.

## Overview

Your app now has two ways to protect pages:

1. **Middleware Protection** (Automatic) - Configured in `src/middleware.ts`
2. **Manual Protection** (Per-page) - Using utilities in page frontmatter

## 1. Middleware Protection (Recommended)

The middleware automatically protects routes defined in `src/middleware.ts`:

```typescript
// Protected routes (require authentication)
const protectedRoutes = [
  '/dashboard',
  '/profile', 
  '/settings',
  '/expenses',
  '/budgets',
];

// Guest-only routes (redirect if authenticated)
const guestOnlyRoutes = [
  '/auth/signin',
  '/auth/signup',
];
```

### Adding New Protected Routes

Just add the route to the `protectedRoutes` array in `src/middleware.ts`:

```typescript
const protectedRoutes = [
  '/dashboard',
  '/profile',
  '/settings',
  '/expenses',
  '/budgets',
  '/new-protected-page', // Add your new route here
];
```

## 2. Manual Page Protection

For more granular control, use the utilities in your page frontmatter:

### Protect a Page (Redirect if Not Authenticated)

```astro
---
// src/pages/protected-page.astro
import { requireAuth } from '@/lib/auth/server-auth-utils';

// This will redirect to /auth/signin if not authenticated
const user = await requireAuth(Astro);
// Now you have access to the authenticated user data
---

<div>
  <h1>Welcome {user.username}!</h1>
  <p>This page is protected</p>
</div>
```

### Redirect Authenticated Users (Login/Signup Pages)

```astro
---
// src/pages/auth/signin.astro
import { redirectIfAuthenticated } from '@/lib/auth/server-auth-utils';

// This will redirect to /dashboard if already authenticated
await redirectIfAuthenticated(Astro);
---

<div>
  <h1>Sign In</h1>
  <!-- Login form here -->
</div>
```

### Check Authentication Without Redirect

```astro
---
// src/pages/conditional-content.astro
import { getAuthenticatedUser } from '@/lib/auth/server-auth-utils';

const user = await getAuthenticatedUser(Astro.cookies);
const isAuthenticated = !!user;
---

<div>
  {isAuthenticated ? (
    <p>Welcome back, {user.username}!</p>
  ) : (
    <p>Please <a href="/auth/signin">sign in</a> to continue</p>
  )}
</div>
```

## 3. Available Utilities

All utilities are in `src/lib/auth/server-auth-utils.ts`:

### `getAuthenticatedUser(cookies)`
- Returns user data if authenticated, `null` if not
- Does not redirect

### `isLoggedIn(cookies)`
- Returns `true` if authenticated, `false` if not
- Convenience wrapper around `getAuthenticatedUser`

### `requireAuth(context, redirectTo?)`
- Requires authentication or redirects
- Default redirect: `/auth/signin`
- Returns user data if authenticated
- Throws redirect response if not authenticated

### `redirectIfAuthenticated(context, redirectTo?)`
- Redirects authenticated users away
- Default redirect: `/dashboard`
- Useful for login/signup pages
- Returns `null` if not authenticated
- Throws redirect response if authenticated

## 4. Current Protected Pages

These pages are currently protected by the middleware:

- `/dashboard/*` - Dashboard pages
- `/profile/*` - User profile pages  
- `/settings/*` - Application settings
- `/expenses/*` - Expense management
- `/budgets/*` - Budget management

## 4.1. Logout System

The logout system provides secure session termination:

### Pages:
- `/auth/logout` - Interactive logout page with confirmation

### API Routes:
- `GET /api/auth/logout` - Direct logout with redirect to home
- `POST /api/auth/logout` - AJAX logout returning JSON response

### Features:
- **Backend Token Invalidation** - Notifies backend to invalidate the session
- **Cookie Cleanup** - Removes HTTP-only auth cookies
- **Graceful Fallback** - Clears cookies even if backend is unreachable
- **User Confirmation** - Interactive page asks for confirmation before logout
- **Loading States** - Shows progress during logout process
- **Error Handling** - Handles network errors and retry options

## 5. Testing Authentication

1. **Visit a protected page without logging in**:
   - Go to `/dashboard`
   - Should redirect to `/auth/signin`

2. **Visit auth pages while logged in**:
   - Log in via `/auth-demo`
   - Visit `/auth/signin`
   - Should redirect to `/dashboard`

3. **Access protected pages while logged in**:
   - Log in via `/auth-demo`
   - Visit `/dashboard`
   - Should show the protected content

## 6. How It Works

Your authentication system uses:

- **HTTP-only cookies** for secure token storage
- **Server-side API routes** (`/api/auth/*`) that proxy to your FastAPI backend
- **Server-side authentication checks** in Astro middleware and page frontmatter
- **Automatic token refresh** handled by the backend integration

This provides maximum security by keeping tokens away from client-side JavaScript while maintaining a smooth user experience.

## 7. Example: Creating a New Protected Page

```astro
---
// src/pages/my-protected-page.astro
import AppLayout from '@/layouts/AppLayout.astro';
import { requireAuth } from '@/lib/auth/server-auth-utils';

// Protect this page
const user = await requireAuth(Astro);
---

<AppLayout title={`Welcome ${user.username}`}>
  <div class="container mx-auto py-8">
    <h1 class="text-3xl font-bold mb-4">Protected Page</h1>
    <p>Hello {user.username}, this page is only accessible to authenticated users!</p>
    
    <div class="mt-4 p-4 bg-green-50 rounded">
      <h2 class="font-semibold">Your Info:</h2>
      <p>Email: {user.email}</p>
      <p>ID: {user.id}</p>
      <p>Verified: {user.email_verified ? 'Yes' : 'No'}</p>
    </div>
  </div>
</AppLayout>
```

That's it! Your pages are now properly protected with server-side authentication checks. 