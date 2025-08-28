#!/bin/bash
# Patent Review System One-Click Startup Script

echo "🚀 Starting Patent Review System..."

# Terminate potentially running old processes
echo "🧹 Cleaning up old processes..."
pkill -f "uvicorn app.__main__:app" 2>/dev/null
pkill -f "python -m app" 2>/dev/null
pkill -f "uvicorn.*6000" 2>/dev/null
pkill -f "vite" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null

# Force cleanup processes occupying ports
if lsof -ti:6000 >/dev/null 2>&1; then
    echo "🔧 Cleaning up processes occupying port 6000..."
    lsof -ti:6000 | xargs kill -9 2>/dev/null || true
fi
if lsof -ti:3000 >/dev/null 2>&1; then
    echo "🔧 Cleaning up processes occupying port 3000..."
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
fi

# Wait for processes to completely terminate
sleep 2

# Start backend
echo "🔧 Starting backend service..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate patent-backend
cd server
uvicorn app.__main__:app --reload --host 0.0.0.0 --port 8080 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Start frontend
echo "🎨 Starting frontend service..."
conda activate patent-frontend
cd client
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
echo "Stop services: ./stop-dev.sh"
echo "View logs: ./logs-dev.sh"
echo ""
echo "🎉 Development environment ready!"