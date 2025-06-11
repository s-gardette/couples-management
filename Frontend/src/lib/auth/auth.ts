import { betterAuth } from "better-auth";

export const auth = betterAuth({
  baseURL: "http://localhost:3000", // Your frontend URL
  trustedOrigins: ["http://localhost:3000", "http://localhost:8000"],
  
  database: {
    // We'll use your backend API instead of direct database access
    provider: "custom",
  },

  // Configure to use your existing backend
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 24 hours
  },

  // Social providers (can be enabled later)
  socialProviders: {
    // github: {
    //   clientId: process.env.GITHUB_CLIENT_ID as string,
    //   clientSecret: process.env.GITHUB_CLIENT_SECRET as string,
    // },
    // google: {
    //   clientId: process.env.GOOGLE_CLIENT_ID as string,
    //   clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    // },
  },

  // Email verification settings
  emailVerification: {
    autoSignInAfterVerification: true,
  },

  // Custom API endpoints to connect to your backend
  endpoints: {
    signUp: {
      path: "/api/auth/register",
    },
    signIn: {
      path: "/api/auth/login", 
    },
    signOut: {
      path: "/api/auth/logout",
    },
    getSession: {
      path: "/api/auth/me",
    },
    forgotPassword: {
      path: "/api/auth/forgot-password",
    },
    resetPassword: {
      path: "/api/auth/reset-password",
    },
    verifyEmail: {
      path: "/api/auth/verify-email",
    },
    updatePassword: {
      path: "/api/users/me/password",
    },
  },

  // Custom fetch function to connect to your backend
  async rateLimit() {
    return true; // Let your backend handle rate limiting
  },
});

export type Session = typeof auth.$Infer.Session; 