#!/bin/bash

# Set required environment variables for Auth.js
export AUTH_SECRET="your-super-secret-auth-secret-key-change-this-in-production-at-least-32-chars"
export AUTH_TRUST_HOST=true
export PUBLIC_API_URL=http://localhost:8000

# Start the development server
bun run dev 