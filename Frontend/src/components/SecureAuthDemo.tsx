import React, { useState } from 'react';
import { SecureAuthProvider, useAuth } from '../lib/auth/secure-auth-context';

// Simple inline login form
function SimpleLoginForm({ onSuccess, onCancel }: { onSuccess: () => void, onCancel: () => void }) {
  const { login, loading } = useAuth();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!formData.email || !formData.password) {
      setError('Please fill in all fields');
      return;
    }

    try {
      await login(formData.email, formData.password);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Secure Login</h3>
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email or Username
            </label>
            <input
              type="text"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter email or username"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter password"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-md disabled:opacity-50"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-2 px-4 rounded-md"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Simple inline register form
function SimpleRegisterForm({ onSuccess, onCancel }: { onSuccess: () => void, onCancel: () => void }) {
  const { register, loading } = useAuth();
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    first_name: '',
    last_name: ''
  });
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!formData.email || !formData.username || !formData.password) {
      setError('Please fill in required fields (email, username, password)');
      return;
    }

    try {
      await register(formData);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">Secure Registration</h3>
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                First Name
              </label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="First name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Last Name
              </label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Last name"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter email"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Username *
            </label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData(prev => ({ ...prev, username: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter username"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Password *
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData(prev => ({ ...prev, password: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter password"
              required
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-md disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Sign Up'}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 py-2 px-4 rounded-md"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Simple auth status component
function AuthStatus() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const [showLoginForm, setShowLoginForm] = useState(false);
  const [showRegisterForm, setShowRegisterForm] = useState(false);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-800 mb-2">
          🔓 Not Authenticated
        </h3>
        <p className="text-blue-700 mb-4">
          Click one of the buttons below to test the secure authentication system:
        </p>
        <div className="flex flex-wrap gap-4">
          <button
            onClick={() => setShowLoginForm(true)}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
          >
            Test Login
          </button>
          <button
            onClick={() => setShowRegisterForm(true)}
            className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors"
          >
            Test Registration
          </button>
        </div>
        
        {showLoginForm && (
          <SimpleLoginForm
            onSuccess={() => setShowLoginForm(false)}
            onCancel={() => setShowLoginForm(false)}
          />
        )}
        
        {showRegisterForm && (
          <SimpleRegisterForm
            onSuccess={() => setShowRegisterForm(false)}
            onCancel={() => setShowRegisterForm(false)}
          />
        )}
      </div>
    );
  }

  // User is authenticated
  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-green-800 mb-4">
        🔒 Authenticated User (Secure Mode)
      </h3>
      <div className="space-y-3">
        <div className="bg-white rounded p-4">
          <h4 className="font-medium text-gray-800 mb-2">User Information:</h4>
          <div className="text-sm text-gray-600 space-y-1">
            <p><strong>ID:</strong> {user?.id}</p>
            <p><strong>Username:</strong> {user?.username}</p>
            <p><strong>Email:</strong> {user?.email}</p>
            <p><strong>Name:</strong> {user?.first_name && user?.last_name ? `${user.first_name} ${user.last_name}` : 'Not provided'}</p>
            <p><strong>Email Verified:</strong> {user?.email_verified ? 'Yes' : 'No'}</p>
            <p><strong>Active:</strong> {user?.is_active ? 'Yes' : 'No'}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors"
        >
          Sign Out
        </button>
      </div>
    </div>
  );
}

// Main demo component with secure provider
export function SecureAuthDemo() {
  return (
    <SecureAuthProvider>
      <div className="space-y-6">
        {/* Security Notice */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-800 mb-4">
            🛡️ Secure Authentication Mode
          </h3>
          <p className="text-green-700 mb-2">
            This uses server-side API routes for enhanced security:
          </p>
          <ul className="text-sm text-green-600 space-y-1 ml-4">
            <li>• Tokens stored in HTTP-only cookies (not accessible to JavaScript)</li>
            <li>• No direct backend API exposure to the browser</li>
            <li>• Server-side proxy handling all sensitive operations</li>
            <li>• CSRF protection with SameSite cookies</li>
            <li>• Automatic token refresh on the server</li>
          </ul>
        </div>

        {/* Features Overview */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            🔐 Secure Authentication Features
          </h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <ul className="space-y-2">
              <li>✅ Email/Username + Password login</li>
              <li>✅ User registration with validation</li>
              <li>✅ Password strength checking</li>
              <li>✅ Email/Username availability checking</li>
              <li>✅ Forgot password functionality</li>
            </ul>
            <ul className="space-y-2">
              <li>✅ Email verification</li>
              <li>✅ JWT tokens in HTTP-only cookies</li>
              <li>✅ Server-side token management</li>
              <li>✅ Protected routes</li>
              <li>✅ Enhanced security measures</li>
            </ul>
          </div>
        </div>

        {/* Authentication Status */}
        <AuthStatus />

        {/* Architecture Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-4">
            🏗️ Secure Architecture
          </h3>
          <p className="text-blue-700 mb-2">Authentication flow:</p>
          <div className="text-sm text-blue-600 space-y-1">
            <p><strong>Frontend</strong> → <strong>Astro API Routes</strong> → <strong>FastAPI Backend</strong></p>
            <ul className="mt-2 ml-4 space-y-1">
              <li>• POST /api/auth/login - Server-side login</li>
              <li>• POST /api/auth/register - Server-side registration</li>
              <li>• POST /api/auth/logout - Server-side logout</li>
              <li>• GET /api/auth/me - Get current user</li>
              <li>• POST /api/auth/refresh - Server-side token refresh</li>
            </ul>
          </div>
        </div>

        {/* Security Benefits */}
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-800 mb-4">
            🔒 Security Benefits
          </h3>
          <div className="text-yellow-700 space-y-2">
            <div className="grid md:grid-cols-2 gap-4 text-sm">
              <div>
                <p><strong>HTTP-Only Cookies:</strong></p>
                <ul className="ml-4 space-y-1">
                  <li>• No XSS token theft</li>
                  <li>• Automatic cookie handling</li>
                  <li>• Secure transmission only</li>
                </ul>
              </div>
              <div>
                <p><strong>Server-Side Proxy:</strong></p>
                <ul className="ml-4 space-y-1">
                  <li>• Backend API not exposed</li>
                  <li>• Centralized security control</li>
                  <li>• Request validation</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Instructions */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-purple-800 mb-4">
            🚀 Implementation Guide
          </h3>
          <div className="text-sm text-purple-700 space-y-2">
            <p><strong>1. Use SecureAuthProvider:</strong></p>
            <pre className="bg-purple-100 p-2 rounded text-xs overflow-x-auto">
{`import { SecureAuthProvider } from './lib/secure-auth-context';

function App() {
  return (
    <SecureAuthProvider>
      <YourAppContent />
    </SecureAuthProvider>
  );
}`}
            </pre>
            
            <p><strong>2. Environment Variables:</strong></p>
            <pre className="bg-purple-100 p-2 rounded text-xs overflow-x-auto">
{`# .env
BACKEND_URL=http://localhost:8000`}
            </pre>
            
            <p><strong>3. Use the secure auth hook:</strong></p>
            <pre className="bg-purple-100 p-2 rounded text-xs overflow-x-auto">
{`const { user, isAuthenticated, login, logout } = useAuth();`}
            </pre>
          </div>
        </div>

        {/* Next Steps */}
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-orange-800 mb-4">
            📋 Next Steps
          </h3>
          <ol className="text-orange-700 space-y-2 list-decimal list-inside">
            <li>Test the secure authentication flow above</li>
            <li>Update your components to use SecureAuthProvider</li>
            <li>Set the BACKEND_URL environment variable</li>
            <li>Remove the old direct auth client if everything works</li>
            <li>Consider adding HTTPS in production for full security</li>
          </ol>
        </div>
      </div>
    </SecureAuthProvider>
  );
} 