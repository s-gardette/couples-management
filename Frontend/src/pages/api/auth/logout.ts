import type { APIRoute } from 'astro';

const BACKEND_URL = import.meta.env.BACKEND_URL || 'http://localhost:8000';

// Handle both GET and POST requests for logout
const logoutHandler = async ({ request, cookies, redirect }: any) => {
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

    // Check if this is a GET request (direct navigation)
    if (request.method === 'GET') {
      // Redirect to home page after logout
      return redirect('/');
    } else {
      // POST request - return JSON response
      return new Response(JSON.stringify({
        message: 'Logout successful'
      }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    }

  } catch (error) {
    console.error('Logout API error:', error);
    
    // Clear cookies even if there's an error
    cookies.delete('access_token', { path: '/' });
    cookies.delete('refresh_token', { path: '/' });
    
    if (request.method === 'GET') {
      return redirect('/?logout=error');
    } else {
      return new Response(JSON.stringify({
        message: 'Logout completed with errors'
      }), {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    }
  }
};

// Export both GET and POST handlers
export const GET: APIRoute = logoutHandler;
export const POST: APIRoute = logoutHandler; 