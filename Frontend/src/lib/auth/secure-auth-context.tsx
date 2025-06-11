import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { secureAuthClient, type User } from './secure-auth-client';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  resendVerification: (email: string) => Promise<void>;
  checkEmailAvailability: (email: string) => Promise<boolean>;
  checkUsernameAvailability: (username: string) => Promise<boolean>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function SecureAuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize authentication state
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      // With HTTP-only cookies, we need to check with the server
      const userData = await secureAuthClient.getMe();
      setUser(userData);
    } catch (error) {
      console.error('Auth initialization error:', error);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const result = await secureAuthClient.login({ email_or_username: email, password });
      setUser(result.user);
    } catch (error) {
      setLoading(false);
      throw error;
    }
    setLoading(false);
  };

  const register = async (data: {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
  }) => {
    setLoading(true);
    try {
      const result = await secureAuthClient.register(data);
      setUser(result.user);
    } catch (error) {
      setLoading(false);
      throw error;
    }
    setLoading(false);
  };

  const logout = async () => {
    setLoading(true);
    try {
      await secureAuthClient.logout();
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      // Still clear user state even if server call fails
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const forgotPassword = async (email: string) => {
    return secureAuthClient.forgotPassword(email);
  };

  const resetPassword = async (token: string, newPassword: string) => {
    return secureAuthClient.resetPassword(token, newPassword);
  };

  const verifyEmail = async (token: string) => {
    await secureAuthClient.verifyEmail(token);
    // Refresh user data after verification
    await refreshUser();
  };

  const resendVerification = async (email: string) => {
    return secureAuthClient.resendVerification(email);
  };

  const checkEmailAvailability = async (email: string) => {
    return secureAuthClient.checkEmailAvailability(email);
  };

  const checkUsernameAvailability = async (username: string) => {
    return secureAuthClient.checkUsernameAvailability(username);
  };

  const refreshUser = async () => {
    try {
      const userData = await secureAuthClient.getMe();
      setUser(userData);
    } catch (error) {
      console.error('Error refreshing user:', error);
      setUser(null);
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    forgotPassword,
    resetPassword,
    verifyEmail,
    resendVerification,
    checkEmailAvailability,
    checkUsernameAvailability,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useSecureAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useSecureAuth must be used within a SecureAuthProvider');
  }
  return context;
}

// Keep the old hook name for backward compatibility
export const useAuth = useSecureAuth; 