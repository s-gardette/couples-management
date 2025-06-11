import type { APIRoute } from 'astro';

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

export const POST: APIRoute = async ({ request, cookies }) => {
  try {
    const accessToken = cookies.get('access_token')?.value;
    
    // If we have a token, notify the backend
    if (accessToken) {
      try {
        await fetch(`${BACKEND_URL}/api/auth/logout`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${accessToken}`,
          },
          body: JSON.stringify({}),
        });
      } catch (error) {
        console.error('Backend logout error:', error);
        // Continue with cookie clearing even if backend call fails
      }
    }

    // Clear auth cookies
    cookies.delete('access_token', { path: '/' });
    cookies.delete('refresh_token', { path: '/' });

    return new Response(JSON.stringify({
      message: 'Logout successful'
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
    });

  } catch (error) {
    console.error('Logout API error:', error);
    
    // Clear cookies even if there's an error
    cookies.delete('access_token', { path: '/' });
    cookies.delete('refresh_token', { path: '/' });
    
    return new Response(JSON.stringify({
      message: 'Logout completed with errors'
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
}; 