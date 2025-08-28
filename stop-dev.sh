#!/bin/bash
# Stop Patent Review System

echo "🛑 Stopping Patent Review System..."

# Terminate backend processes
echo "🔧 Stopping backend service..."
pkill -f "uvicorn app.__main__:app"
pkill -f "python -m app"
pkill -f "uvicorn.*8080"

# Force cleanup processes occupying port 8080
if lsof -ti:8080 >/dev/null 2>&1; then
    echo "🔧 Cleaning up processes occupying port 8080..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
fi

# Terminate frontend processes
echo "🎨 Stopping frontend service..."
pkill -f "vite"
pkill -f "npm run dev"

# Wait for processes to completely terminate
sleep 2

echo "✅ All services stopped"