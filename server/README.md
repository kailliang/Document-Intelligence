# Patent Reviewer Backend

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

## First-time setup

```sh
# Create a virtual environment
python -m venv env

# Activate your virtual environment
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Make sure you create a .env file (see .env.example) with the OpenAI API key we've provided.

## Running locally

To run the backend locally, with auto-reload on code changes,

```sh
uvicorn app.__main__:app --reload
```

## DB

On start-up, the app will initialise an in-memory SQLite DB, and fill it with some seed data. If you decide that you want to reset your changes, all you need to do is re-run the backend.
