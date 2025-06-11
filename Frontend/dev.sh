#!/bin/bash

# Couples Management - Frontend Development Script
# This script helps you start the frontend development server

echo "🚀 Starting Couples Management Frontend Development Server..."
echo ""

# Check if we're in the Frontend directory
if [[ ! -f "package.json" ]]; then
    echo "❌ Error: package.json not found. Please run this script from the Frontend directory."
    echo "   Usage: cd Frontend && ./dev.sh"
    exit 1
fi

# Set environment variables for development
export PUBLIC_API_URL="http://localhost:8000"
export BACKEND_URL="http://localhost:8000"

echo "🔧 Environment Configuration:"
echo "   - Frontend API URL: $PUBLIC_API_URL"
echo "   - Backend URL (for secure routes): $BACKEND_URL"
echo "   - Make sure your FastAPI backend is running on localhost:8000"
echo ""

# Check if node_modules exists, if not install dependencies
if [[ ! -d "node_modules" ]]; then
    echo "📦 Installing dependencies..."
    bun install
    echo ""
fi

# Start the development server
echo "🌟 Starting Astro development server..."
echo "   - Frontend will be available at http://localhost:4321"
echo "   - Demo page: http://localhost:4321/auth-demo"
echo "   - Secure demo: http://localhost:4321/secure-auth-demo"
echo "   - Dashboard: http://localhost:4321/dashboard"
echo ""

bun run dev 