# Patent Review System Development Guide

## 🚀 Quick Start

### One-Click Start (Recommended)
```bash
./start-dev.sh    # Start frontend and backend services
```

### Stop Services
```bash
./stop-dev.sh     # Stop all services
```

### Check Status
```bash
./logs-dev.sh     # Check process status and connection tests
```

## 📱 Access URLs

After successful startup:
- **Frontend Application**: http://localhost:5173
- **Backend API**: http://localhost:8000  
- **API Documentation**: http://localhost:8000/docs

## 🔧 Manual Start (Alternative Method)

### Backend
```bash
conda activate patent-backend
cd server
uvicorn app.__main__:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
conda activate patent-frontend
cd client
npm run dev
```

## 💡 Development Tips

- Using `start-dev.sh` will automatically clean up old processes and start new services.
- The script will display process IDs for easy debugging.
- If a port is occupied, the script will automatically terminate the conflicting process.
- All services support hot-reloading; code changes will trigger an automatic restart.

The environment is configured. Happy coding!