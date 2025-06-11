import React, { useState } from 'react';
import { useAuth } from '../../lib/auth-context';

interface UserProfileProps {
  className?: string;
  showFullProfile?: boolean;
}

export function UserProfile({ className = '', showFullProfile = false }: UserProfileProps) {
  const { user, logout, loading } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);

  if (!user) return null;

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const displayName = user.first_name && user.last_name 
    ? `${user.first_name} ${user.last_name}`
    : user.username;

  const initials = user.first_name && user.last_name
    ? `${user.first_name[0]}${user.last_name[0]}`
    : user.username.slice(0, 2);

  if (showFullProfile) {
    return (
      <div className={`bg-white rounded-lg shadow p-6 ${className}`}>
        <div className="flex items-center space-x-4 mb-6">
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center text-white text-lg font-semibold">
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={displayName}
                className="w-16 h-16 rounded-full object-cover"
              />
            ) : (
              initials.toUpperCase()
            )}
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">{displayName}</h2>
            <p className="text-gray-600">@{user.username}</p>
            <p className="text-gray-600">{user.email}</p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Account Status</label>
              <p className={`text-sm font-semibold ${user.is_active ? 'text-green-600' : 'text-red-600'}`}>
                {user.is_active ? 'Active' : 'Inactive'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Email Verified</label>
              <p className={`text-sm font-semibold ${user.email_verified ? 'text-green-600' : 'text-yellow-600'}`}>
                {user.email_verified ? 'Verified' : 'Pending'}
              </p>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Member Since</label>
            <p className="text-sm text-gray-600">
              {new Date(user.created_at).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
              })}
            </p>
          </div>

          {user.last_login_at && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Last Login</label>
              <p className="text-sm text-gray-600">
                {new Date(user.last_login_at).toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })}
              </p>
            </div>
          )}
        </div>

        <div className="mt-6 pt-6 border-t border-gray-200">
          <button
            onClick={handleLogout}
            disabled={loading}
            className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {loading ? 'Signing out...' : 'Sign Out'}
          </button>
        </div>
      </div>
    );
  }

  // Compact dropdown version
  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center space-x-2 p-2 rounded-md hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={displayName}
              className="w-8 h-8 rounded-full object-cover"
            />
          ) : (
            initials.toUpperCase()
          )}
        </div>
        <span className="text-sm font-medium text-gray-700 hidden sm:block">
          {displayName}
        </span>
        <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {showDropdown && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
          <div className="py-1">
            <div className="px-4 py-3 border-b border-gray-200">
              <p className="text-sm font-medium text-gray-800">{displayName}</p>
              <p className="text-sm text-gray-600">{user.email}</p>
            </div>
            
            <div className="px-4 py-2">
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>Status:</span>
                <span className={user.is_active ? 'text-green-600' : 'text-red-600'}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 mt-1">
                <span>Email:</span>
                <span className={user.email_verified ? 'text-green-600' : 'text-yellow-600'}>
                  {user.email_verified ? 'Verified' : 'Pending'}
                </span>
              </div>
            </div>

            <div className="border-t border-gray-200">
              <button
                onClick={() => {
                  setShowDropdown(false);
                  handleLogout();
                }}
                disabled={loading}
                className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 disabled:text-gray-400 disabled:hover:bg-transparent"
              >
                {loading ? 'Signing out...' : 'Sign Out'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close dropdown */}
      {showDropdown && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowDropdown(false)}
        />
      )}
    </div>
  );
} 