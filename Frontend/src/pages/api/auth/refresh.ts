import type { APIRoute } from 'astro';

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const POST: APIRoute = async ({ cookies }) => {
  try {
    const refreshToken = cookies.get('refresh_token')?.value;
    
    if (!refreshToken) {
      return new Response(JSON.stringify({
        detail: 'No refresh token available'
      }), {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    }

    // Forward the request to the FastAPI backend
    const response = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      // Clear cookies if refresh fails
      cookies.delete('access_token', { path: '/' });
      cookies.delete('refresh_token', { path: '/' });
      
      return new Response(JSON.stringify(data), {
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    }

    // Update cookies with new tokens
    if (data.access_token) {
      cookies.set('access_token', data.access_token, {
        httpOnly: true,
        secure: import.meta.env.PROD,
        sameSite: 'strict',
        maxAge: 60 * 60 * 24, // 24 hours
        path: '/',
      });
    }

    if (data.refresh_token) {
      cookies.set('refresh_token', data.refresh_token, {
        httpOnly: true,
        secure: import.meta.env.PROD,
        sameSite: 'strict',
        maxAge: 60 * 60 * 24 * 7, // 7 days
        path: '/',
      });
    }

    return new Response(JSON.stringify({
      message: 'Token refreshed successfully'
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
    });

  } catch (error) {
    console.error('Refresh API error:', error);
    
    // Clear cookies on error
    cookies.delete('access_token', { path: '/' });
    cookies.delete('refresh_token', { path: '/' });
    
    return new Response(JSON.stringify({
      detail: 'Internal server error'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
}; 