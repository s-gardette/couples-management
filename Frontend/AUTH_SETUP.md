# Authentication System Setup

This document explains how to use the comprehensive authentication system built with Better Auth that connects to your backend API.

## Overview

The authentication system provides:

- ✅ **Complete Auth Flow**: Login, registration, password reset, email verification
- ✅ **Backend Integration**: Connects directly to your existing FastAPI backend at `localhost:8000`
- ✅ **JWT Token Management**: Automatic token storage, refresh, and cleanup
- ✅ **Form Validation**: Real-time validation with password strength checking
- ✅ **Email/Username Availability**: Live checking during registration
- ✅ **Protected Routes**: Component-based route protection
- ✅ **User Management**: Profile display, logout, account status
- ✅ **TypeScript Support**: Full type safety throughout

## Backend Endpoints Used

The system connects to these endpoints on your backend:

```
POST /api/auth/register          # User registration
POST /api/auth/login             # User login
POST /api/auth/logout            # User logout
POST /api/auth/refresh           # Token refresh
GET  /api/auth/me                # Get current user
POST /api/auth/forgot-password   # Request password reset
POST /api/auth/reset-password    # Reset password with token
POST /api/auth/verify-email      # Verify email with token
POST /api/auth/resend-verification # Resend verification email
POST /api/auth/check-email       # Check email availability
POST /api/auth/check-username    # Check username availability
PUT  /api/users/me/password      # Update user password
```

## Quick Start

### 1. Wrap Your App with AuthProvider

```tsx
import { AuthProvider } from './components/auth';

function App() {
  return (
    <AuthProvider>
      <YourAppContent />
    </AuthProvider>
  );
}
```

### 2. Use Authentication in Components

```tsx
import { useAuth, ProtectedRoute } from './components/auth';

function Dashboard() {
  const { user, isAuthenticated, logout } = useAuth();
  
  if (!isAuthenticated) {
    return <div>Please sign in</div>;
  }

  return (
    <div>
      <h1>Welcome, {user?.username}!</h1>
      <button onClick={logout}>Sign Out</button>
    </div>
  );
}

// Or use ProtectedRoute wrapper
function ProtectedDashboard() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
```

### 3. Add Authentication Modal

```tsx
import { AuthModal } from './components/auth';

function NavBar() {
  const [showAuth, setShowAuth] = useState(false);
  
  return (
    <nav>
      <button onClick={() => setShowAuth(true)}>
        Sign In
      </button>
      
      <AuthModal
        isOpen={showAuth}
        onClose={() => setShowAuth(false)}
        initialMode="login" // or "register" or "forgot-password"
        onSuccess={() => {
          setShowAuth(false);
          // Handle successful auth
        }}
      />
    </nav>
  );
}
```

### 4. Display User Profile

```tsx
import { UserProfile } from './components/auth';

function Header() {
  return (
    <header>
      <h1>My App</h1>
      <UserProfile /> {/* Shows dropdown with user info and logout */}
    </header>
  );
}

// Or show full profile page
function ProfilePage() {
  return (
    <UserProfile showFullProfile={true} />
  );
}
```

## Available Components

### AuthProvider
Context provider that manages authentication state.

```tsx
<AuthProvider>
  {/* Your app */}
</AuthProvider>
```

### useAuth Hook
Access authentication state and functions.

```tsx
const {
  user,                    // Current user object
  loading,                 // Loading state
  isAuthenticated,         // Authentication status
  login,                   // Login function
  register,                // Registration function
  logout,                  // Logout function
  forgotPassword,          // Request password reset
  resetPassword,           // Reset password with token
  verifyEmail,             # Verify email with token
  resendVerification,      // Resend verification email
  checkEmailAvailability,  // Check if email is available
  checkUsernameAvailability, // Check if username is available
  updatePassword,          // Update current user's password
  refreshUser              // Refresh user data
} = useAuth();
```

### AuthModal
Complete authentication modal with all forms.

```tsx
<AuthModal
  isOpen={true}
  onClose={() => {}}
  initialMode="login" // "login" | "register" | "forgot-password"
  onSuccess={() => {}}
/>
```

### Individual Forms
Use individual forms if you prefer custom layouts.

```tsx
import { LoginForm, RegisterForm, ForgotPasswordForm } from './components/auth';

<LoginForm
  onSuccess={() => {}}
  onSwitchToRegister={() => {}}
  onSwitchToForgotPassword={() => {}}
/>

<RegisterForm
  onSuccess={() => {}}
  onSwitchToLogin={() => {}}
/>

<ForgotPasswordForm
  onSuccess={() => {}}
  onSwitchToLogin={() => {}}
/>
```

### ProtectedRoute
Protect components/pages that require authentication.

```tsx
<ProtectedRoute
  showModal={true}        // Show auth modal if not authenticated
  redirectTo="/login"     // Or redirect to this URL
  fallback={<LoginPage />} // Or show this component
>
  <ProtectedContent />
</ProtectedRoute>
```

### UserProfile
Display user information and logout option.

```tsx
<UserProfile
  showFullProfile={false} // true for full profile page
  className="custom-class"
/>
```

## Configuration

### Backend URL
Update the API base URL in `src/lib/auth-client.ts`:

```typescript
const API_BASE_URL = 'http://localhost:8000'; // Change this to your backend URL
```

### Token Storage
Tokens are automatically stored in localStorage. The system handles:
- Access token storage and retrieval
- Refresh token management
- Automatic token refresh on 401 responses
- Token cleanup on logout

## User Data Structure

```typescript
interface User {
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
```

## Error Handling

The system includes comprehensive error handling:

- Network errors
- Validation errors
- Authentication failures
- Token expiration
- Backend API errors

Errors are displayed in the UI and can be caught in your components:

```tsx
try {
  await login(email, password);
} catch (error) {
  console.error('Login failed:', error.message);
}
```

## Demo Page

Visit `/auth-demo` to see a live demonstration of all authentication features and components.

## Security Features

- ✅ **Secure Token Storage**: Tokens stored in localStorage with automatic cleanup
- ✅ **Automatic Token Refresh**: Seamless token renewal on expiration
- ✅ **Password Strength Validation**: Real-time password strength checking
- ✅ **Email/Username Validation**: Live availability checking
- ✅ **CSRF Protection**: Through backend integration
- ✅ **Input Sanitization**: Comprehensive form validation
- ✅ **Error Handling**: Graceful error handling and user feedback

## Best Practices

1. **Always wrap your app with AuthProvider** at the root level
2. **Use ProtectedRoute** for pages that require authentication
3. **Check isAuthenticated** before accessing user data
4. **Handle loading states** to improve user experience
5. **Implement proper error boundaries** for authentication errors
6. **Use the provided TypeScript types** for type safety

## Troubleshooting

### Common Issues

1. **Backend not responding**: Ensure your backend is running on `localhost:8000`
2. **CORS errors**: Configure CORS in your backend to allow frontend origin
3. **Token refresh fails**: Check backend refresh token endpoint implementation
4. **Forms not submitting**: Check browser console for validation errors

### Debug Mode
Enable debug logging by adding this to your console:

```javascript
localStorage.setItem('auth-debug', 'true');
```

This will log authentication operations to the browser console.

## Support

If you encounter issues:

1. Check the browser console for error messages
2. Verify your backend endpoints are working with the expected request/response format
3. Ensure CORS is properly configured on your backend
4. Test individual authentication operations using the demo page at `/auth-demo` 