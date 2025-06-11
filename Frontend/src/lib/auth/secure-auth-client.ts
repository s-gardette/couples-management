// Secure auth client that uses server-side API routes
// This prevents direct exposure of your backend API

export interface User {
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

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface LoginData {
  email_or_username: string;
  password: string;
}

class SecureAuthClient {
  private async makeRequest(endpoint: string, options: RequestInit = {}) {
    const url = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    
    const response = await fetch(url, {
      credentials: 'include', // Include cookies in requests
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string>),
      },
      ...options,
    });

    return response;
  }

  async register(data: RegisterData): Promise<{ user: User; message: string }> {
    const response = await this.makeRequest('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || 'Registration failed');
    }

    return result;
  }

  async login(data: LoginData): Promise<{ user: User; message: string }> {
    const response = await this.makeRequest('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.detail || 'Login failed');
    }

    return result;
  }

  async logout(): Promise<void> {
    try {
      await this.makeRequest('/api/auth/logout', {
        method: 'POST',
      });
    } catch (error) {
      console.error('Logout error:', error);
      // Don't throw - logout should always succeed on client side
    }
  }

  async getMe(): Promise<User | null> {
    try {
      const response = await this.makeRequest('/api/auth/me');
      
      if (!response.ok) {
        return null;
      }

      return await response.json();
    } catch (error) {
      console.error('Get user error:', error);
      return null;
    }
  }

  async refreshToken(): Promise<boolean> {
    try {
      const response = await this.makeRequest('/api/auth/refresh', {
        method: 'POST',
      });

      return response.ok;
    } catch (error) {
      console.error('Token refresh error:', error);
      return false;
    }
  }

  // For the remaining methods, we'll still use direct calls since they don't handle sensitive tokens
  // But you can move these to server-side routes too if needed
  async forgotPassword(email: string): Promise<void> {
    const BACKEND_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send reset email');
    }
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    const BACKEND_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token,
        new_password: newPassword,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Password reset failed');
    }
  }

  async verifyEmail(token: string): Promise<void> {
    const BACKEND_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/auth/verify-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ token }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Email verification failed');
    }
  }

  async resendVerification(email: string): Promise<void> {
    const BACKEND_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/auth/resend-verification`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to resend verification email');
    }
  }

  async checkEmailAvailability(email: string): Promise<boolean> {
    const BACKEND_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/auth/check-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) return false;
    
    const data = await response.json();
    return data.available;
  }

  async checkUsernameAvailability(username: string): Promise<boolean> {
    const BACKEND_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${BACKEND_URL}/api/auth/check-username`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username }),
    });

    if (!response.ok) return false;
    
    const data = await response.json();
    return data.available;
  }

  // This method is no longer needed since we use HTTP-only cookies
  isAuthenticated(): boolean {
    // We can't determine this client-side anymore with HTTP-only cookies
    // Instead, we need to check with the server
    return false; // Will be determined by the auth context through getMe()
  }
}

export const secureAuthClient = new SecureAuthClient(); 