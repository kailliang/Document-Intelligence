# Document Intelligence Backend

## Layout

Application code is in the `app/` directory. Everything under `app/internal/` should not be modified, but feel free to take a look at the internals - think of it as a third party library.

```
app
├── __main__.py # FastAPI app, and routes
├── models.py # DB models
├── schemas.py # Schema objects
├── internal
│   ├── ai.py # LLM Integration
│   ├── data.py # Seed data
│   └── db.py # Database utils
└
```

## Environment Setup

### Prerequisites
- Python 3.13 or higher
- Virtual environment support

### First-time setup

```sh
# Create an isolated virtual environment
python3 -m venv .venv

# Activate your virtual environment
source .venv/bin/activate

# Upgrade pip to latest version
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-test.txt
```

### Environment Configuration
Make sure you create a `.env` file (see `.env.example`) with the required API keys:
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Verify Installation
```sh
# Activate environment
source .venv/bin/activate

# Test installation
python -c "import fastapi; print('✅ Backend environment ready!')"
```

## Running locally

### Using Virtual Environment
```sh
# Activate virtual environment
source .venv/bin/activate

# Start with auto-reload
uvicorn app.__main__:app --reload --host 0.0.0.0 --port 8080
```

### Using Development Scripts
From project root directory:
```sh
# Automatic startup (uses virtual environment)
./start-dev.sh

# Manual backend only
cd server && source .venv/bin/activate && uvicorn app.__main__:app --reload
```

