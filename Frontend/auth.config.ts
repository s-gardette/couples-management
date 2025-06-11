import { defineConfig } from 'auth-astro';
import Credentials from '@auth/core/providers/credentials';

export default defineConfig({
  secret: process.env.AUTH_SECRET || 'your-super-secret-auth-secret-key-change-this-in-production-at-least-32-chars',
  trustHost: true,
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        try {
          // Connect to your FastAPI backend - updated to correct endpoint and field name
          const response = await fetch('http://localhost:8000/api/auth/login', {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email_or_username: credentials.email,
              password: credentials.password
            })
          });
          
          if (response.ok) {
            const data = await response.json();
            // Return user object that will be stored in the session
            return {
              id: data.user?.id || data.id,
              email: data.user?.email || data.email,
              name: data.user?.username || data.username,
              // Add any other user properties from your backend
            };
          }
          
          // If login failed, return null
          return null;
        } catch (error) {
          console.error('Auth error:', error);
          return null;
        }
      }
    })
  ],
  session: { 
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  callbacks: {
    async jwt({ token, user }) {
      // Persist the user ID to the token right after signin
      if (user) {
        token.id = user.id as string;
      }
      return token;
    },
    async session({ session, token }) {
      // Send properties to the client
      if (token && session.user) {
        session.user.id = token.id as string;
      }
      return session;
    },
  },
}); 