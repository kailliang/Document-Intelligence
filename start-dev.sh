#!/bin/bash
# Document Intelligence System One-Click Startup Script

echo "🚀 Starting Document Intelligence System..."

# Terminate potentially running old processes
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn app.__main__:app" 2>/dev/null
pkill -f "python -m app" 2>/dev/null
pkill -f "uvicorn.*8080" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# Force cleanup processes occupying ports
if lsof -ti:8080 >/dev/null 2>&1; then
    echo "🔧 Cleaning up processes occupying port 8080..."
    lsof -ti:8080 | xargs kill -9 2>/dev/null || true
fi
if lsof -ti:3000 >/dev/null 2>&1; then
    echo "🔧 Cleaning up processes occupying port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

# Wait for processes to completely terminate
sleep 2

# Start backend with virtual environment
echo "🔧 Starting backend service..."
cd server
if [ ! -d ".venv" ]; then
    echo "❌ Backend virtual environment not found. Please run setup first."
    echo "   Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
source .venv/bin/activate
uvicorn app.__main__:app --reload --host 0.0.0.0 --port 8080 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Start frontend with nvm
echo "🎨 Starting frontend service..."
cd client
# Check if nvm is available and .nvmrc exists
if command -v nvm >/dev/null 2>&1 && [ -f ".nvmrc" ]; then
    echo "🔧 Using Node.js version from .nvmrc..."
    nvm use
else
    echo "⚠️  nvm not found or .nvmrc missing, using system Node.js"
fi
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
sleep 3

echo ""
echo "✅ Services started successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📱 Frontend App:  http://localhost:3000"
echo "🔧 Backend API:   http://localhost:8080"
echo "📚 API Docs:      http://localhost:8080/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Process IDs: Backend=$BACKEND_PID, Frontend=$FRONTEND_PID"
echo ""
echo "🔧 Environment Info:"
echo "   Backend: Python virtual environment (server/.venv)"
echo "   Frontend: Node.js $(cd client && node --version 2>/dev/null || echo 'N/A') via nvm"
echo ""
echo "Stop services: ./stop-dev.sh"
echo "View logs: ./logs-dev.sh"
echo ""
echo "🎉 Development environment ready!"