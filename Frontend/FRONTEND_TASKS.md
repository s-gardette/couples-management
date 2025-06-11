# 🚀 Frontend Development Tasks - Household Management App

## Overview
Building a modern frontend using **Astro + TypeScript + Tailwind + shadcn/ui + React + Tauri** that connects to our FastAPI backend and works as both a web app and Android app.

**Tech Stack:**
- **Framework:** Astro (for SSG/SSR performance)
- **UI Components:** React + shadcn/ui 
- **Styling:** Tailwind CSS
- **Authentication:** Auth.js
- **Mobile:** Tauri (Android + Web)
- **Language:** TypeScript
- **Backend:** FastAPI (http://localhost:8000)

---

## Phase 1: Project Foundation 🏗️

### Task 1.1: Initialize Astro Project
```bash
# Create new Astro project with TypeScript
bun create astro@latest . -- --template minimal --typescript

# Install essential dependencies
bun install @astrojs/react @astrojs/tailwind @astrojs/node
bun install react react-dom @types/react @types/react-dom
```

**Deliverables:**
- [ ] Working Astro project with TypeScript
- [ ] React integration configured
- [ ] Basic project structure

### Task 1.2: Configure Astro for Hybrid Rendering
```js
// astro.config.mjs
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import node from '@astrojs/node';

export default defineConfig({
  integrations: [react(), tailwind()],
  output: 'hybrid', // For SSR + SSG
  adapter: node({
    mode: 'standalone'
  })
});
```

**Deliverables:**
- [ ] Hybrid rendering configured
- [ ] React and Tailwind integrated
- [ ] Node adapter for SSR

### Task 1.3: Setup TypeScript Configuration
```json
// tsconfig.json updates
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@/components/*": ["./src/components/*"],
      "@/lib/*": ["./src/lib/*"],
      "@/types/*": ["./src/types/*"]
    }
  }
}
```

**Deliverables:**
- [ ] TypeScript strict mode enabled
- [ ] Path aliases configured
- [ ] Type definitions ready

---

## Phase 2: Styling & UI Foundation 🎨

### Task 2.1: Setup Tailwind CSS
```bash
# Tailwind should be auto-configured by Astro
# Add custom configuration
bun install tailwindcss-animate class-variance-authority clsx tailwind-merge
```

```js
// tailwind.config.mjs
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        // ... shadcn color system
      }
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

**Deliverables:**
- [ ] Tailwind CSS fully configured
- [ ] Custom CSS variables for theming
- [ ] Animation utilities available

### Task 2.2: Setup shadcn/ui Components
```bash
# Install shadcn/ui CLI and initialize
npx shadcn-ui@latest init

# Install essential components
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add card
npx shadcn-ui@latest add form
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
```

**Deliverables:**
- [ ] shadcn/ui configured for Astro
- [ ] Essential UI components installed
- [ ] Component library ready

### Task 2.3: Create Layout System
```tsx
// src/layouts/BaseLayout.astro
// src/layouts/AuthLayout.astro  
// src/layouts/DashboardLayout.astro
```

**Deliverables:**
- [ ] Base layout with navigation
- [ ] Auth-specific layout
- [ ] Dashboard layout with sidebar
- [ ] Responsive design implemented

---

## Phase 3: Authentication Setup 🔐

### Task 3.1: Install and Configure Auth.js
```bash
# Install Auth.js for Astro
bun install @auth/core @auth/astro
bun install @auth/core/providers/credentials
bun install @auth/core/providers/google # Optional OAuth
```

```ts
// src/auth.config.ts
import { defineConfig } from "@auth/astro"
import Credentials from "@auth/core/providers/credentials"

export default defineConfig({
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        // Connect to your FastAPI backend
        const response = await fetch('http://localhost:8000/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password
          })
        })
        
        if (response.ok) {
          const user = await response.json()
          return user
        }
        return null
      }
    })
  ],
  session: { strategy: "jwt" },
  pages: {
    signIn: '/auth/signin',
    signUp: '/auth/signup'
  }
})
```

**Deliverables:**
- [ ] Auth.js configured for Astro
- [ ] Credentials provider connected to backend
- [ ] JWT session strategy enabled
- [ ] Custom auth pages configured

### Task 3.2: Create Auth API Routes
```ts
// src/pages/api/auth/[...astro].ts
import { AstroAuth } from "@auth/astro"
import authConfig from "../../../auth.config"

export const { GET, POST } = AstroAuth(authConfig)
```

**Deliverables:**
- [ ] Auth API routes created
- [ ] Authentication endpoints working
- [ ] Session management functional

### Task 3.3: Create Authentication Pages
```astro
<!-- src/pages/auth/signin.astro -->
<!-- src/pages/auth/signup.astro -->
<!-- src/pages/auth/signout.astro -->
```

**Page Features:**
- [ ] Sign-in form with email/password
- [ ] Sign-up form with validation
- [ ] Sign-out confirmation
- [ ] Error handling and feedback
- [ ] Redirect after authentication

### Task 3.4: Create Auth Components
```tsx
// src/components/auth/SignInForm.tsx
// src/components/auth/SignUpForm.tsx
// src/components/auth/AuthGuard.tsx
// src/components/auth/UserMenu.tsx
```

**Component Features:**
- [ ] Reusable form components
- [ ] Auth state management
- [ ] Protected route wrapper
- [ ] User menu with profile/logout

---

## Phase 4: Backend Integration 🔌

### Task 4.1: Setup API Client
```ts
// src/lib/api.ts
class ApiClient {
  private baseURL = 'http://localhost:8000'
  
  async request(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseURL}${endpoint}`
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }
    
    const response = await fetch(url, config)
    return response.json()
  }
  
  // Auth methods
  async login(email: string, password: string) { ... }
  async register(userData: any) { ... }
  
  // Expense methods
  async getExpenses() { ... }
  async createExpense(expense: any) { ... }
  
  // Household methods  
  async getHouseholds() { ... }
}

export const api = new ApiClient()
```

**Deliverables:**
- [ ] Centralized API client
- [ ] Type-safe API methods
- [ ] Error handling
- [ ] Authentication token management

### Task 4.2: Define TypeScript Types
```ts
// src/types/api.ts
export interface User {
  id: string
  email: string
  username: string
  is_active: boolean
}

export interface Household {
  id: string
  name: string
  description?: string
  members: User[]
}

export interface Expense {
  id: string
  title: string
  amount: number
  category: string
  household_id: string
  created_by: string
  date: string
}

// ... more types based on backend schemas
```

**Deliverables:**
- [ ] Complete type definitions
- [ ] Matches backend API schemas
- [ ] Type safety across app

---

## Phase 5: Core Pages & Routing 📱

### Task 5.1: Create Base Routes
```
src/pages/
├── index.astro              # Landing page
├── dashboard/
│   ├── index.astro          # Dashboard home
│   ├── expenses/
│   │   ├── index.astro      # Expense list  
│   │   ├── new.astro        # Create expense
│   │   └── [id].astro       # Expense detail
│   └── households/
│       ├── index.astro      # Household list
│       └── [id].astro       # Household detail
└── auth/
    ├── signin.astro         # Sign in
    ├── signup.astro         # Sign up
    └── signout.astro        # Sign out
```

**Deliverables:**
- [ ] Landing page with auth CTA
- [ ] Dashboard with navigation
- [ ] Basic CRUD pages for expenses
- [ ] Household management pages
- [ ] Proper routing structure

### Task 5.2: Implement Protected Routes
```tsx
// src/components/auth/AuthGuard.tsx
import { getSession } from "@auth/astro/client"

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const session = getSession()
  
  if (!session) {
    // Redirect to signin
    return <Navigate to="/auth/signin" />
  }
  
  return <>{children}</>
}
```

**Deliverables:**
- [ ] Route protection implemented
- [ ] Redirect logic for unauthenticated users
- [ ] Session state management

---

## Phase 6: Mobile App with Tauri 📱

### Task 6.1: Setup Tauri
```bash
# Install Tauri CLI
cargo install tauri-cli

# Initialize Tauri in project
cargo tauri init

# Install Tauri API for frontend
bun install @tauri-apps/api
```

**Deliverables:**
- [ ] Tauri configured for mobile
- [ ] Rust backend initialized
- [ ] Mobile APIs available

### Task 6.2: Configure for Android
```toml
# src-tauri/tauri.conf.json
{
  "build": {
    "beforeDevCommand": "bun run dev",
    "beforeBuildCommand": "bun run build",
    "devPath": "http://localhost:4321",
    "distDir": "../dist"
  },
  "tauri": {
    "bundle": {
      "active": true,
      "targets": ["deb", "appimage", "nsis", "dmg", "updater"],
      "identifier": "com.household.manager",
      "icon": ["icons/32x32.png", "icons/128x128.png", "icons/icon.icns", "icons/icon.ico"]
    },
    "android": {
      "minSdkVersion": 24
    }
  }
}
```

**Setup Android:**
```bash
# Install Android targets
rustup target add aarch64-linux-android armv7-linux-androideabi i686-linux-android x86_64-linux-android

# Generate Android project
cargo tauri android init
```

**Deliverables:**
- [ ] Android build configuration
- [ ] App icons and metadata
- [ ] Development and production builds

### Task 6.3: Mobile-Specific Adaptations
```tsx
// src/components/mobile/MobileNav.tsx
// src/components/mobile/TouchOptimized.tsx
```

**Mobile Features:**
- [ ] Touch-optimized interface
- [ ] Mobile navigation patterns
- [ ] Responsive breakpoints
- [ ] Native mobile feel

---

## Phase 7: Development & Build Setup ⚙️

### Task 7.1: Setup Development Scripts
```json
// package.json
{
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "tauri:dev": "cargo tauri dev",
    "tauri:build": "cargo tauri build",
    "tauri:android": "cargo tauri android dev",
    "tauri:android:build": "cargo tauri android build"
  }
}
```

### Task 7.2: Environment Configuration
```bash
# .env
PUBLIC_API_URL=http://localhost:8000
AUTH_SECRET=your-secret-key
AUTH_URL=http://localhost:4321
```

**Deliverables:**
- [ ] Development environment configured
- [ ] Build scripts working
- [ ] Environment variables setup

---

## Success Criteria ✅

**Web App:**
- [ ] Responsive design works on all devices
- [ ] Authentication flow complete
- [ ] Can create/view/edit expenses
- [ ] Household management functional
- [ ] Connects to FastAPI backend

**Android App:**
- [ ] Builds successfully with Tauri
- [ ] Native mobile experience
- [ ] Same functionality as web app
- [ ] Proper Android packaging

**Code Quality:**
- [ ] TypeScript strict mode passing
- [ ] Components properly typed
- [ ] Error handling implemented
- [ ] Performance optimized

---

## References 📚

- **Auth.js Documentation:** https://authjs.dev/getting-started
- **Backend API:** http://localhost:8000/docs
- **Astro Docs:** https://docs.astro.build/
- **Tauri Mobile:** https://beta.tauri.app/guides/develop/mobile/
- **shadcn/ui:** https://ui.shadcn.com/

---

## Next Steps After Basic Auth Setup

1. **Enhanced UI/UX:** Complex dashboard layouts, data visualization
2. **Real-time Features:** WebSocket integration for live updates  
3. **Offline Support:** PWA capabilities, local storage
4. **Advanced Auth:** OAuth providers (Google, GitHub)
5. **Mobile Features:** Push notifications, native device APIs
6. **Performance:** SSR optimization, caching strategies 