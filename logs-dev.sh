#!/bin/bash
# View system logs

echo "📋 Patent Review System Process Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check backend process
BACKEND_PID=$(pgrep -f "uvicorn app.__main__:app")
if [ -n "$BACKEND_PID" ]; then
    echo "✅ Backend running (PID: $BACKEND_PID)"
else
    echo "❌ Backend not running"
fi

# Check frontend process
FRONTEND_PID=$(pgrep -f "vite")
if [ -n "$FRONTEND_PID" ]; then
    echo "✅ Frontend running (PID: $FRONTEND_PID)"
else
    echo "❌ Frontend not running"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check port usage
echo "🌐 Port Status:"
netstat -an | grep -E "(3000|8080)" | grep LISTEN || echo "❌ No listening ports found"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test service availability
echo "🔍 Service Connection Test:"
if curl -s http://localhost:8080/docs > /dev/null; then
    echo "✅ Backend API accessible"
else
    echo "❌ Backend API not accessible"
fi

if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend app accessible"
else
    echo "❌ Frontend app not accessible"
fi