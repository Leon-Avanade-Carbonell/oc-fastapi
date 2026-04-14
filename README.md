# FastAPI Hello World

A simple FastAPI project with a hello-world endpoint.

<!-- AUTO-GENERATED: setup -->
## Setup

### Option 1: Using pip and venv (Standard)

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   ```bash
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   make install
   # or
   pip install -r requirements.txt
   ```

### Option 2: Using uv (Faster alternative, especially recommended for Windows)

> **Note:** `uv` must be installed on your system. See [uv installation](https://docs.astral.sh/uv/getting-started/installation/).

1. **Install dependencies with uv:**
   ```bash
   uv pip install -r requirements.txt
   ```

2. **Activate the virtual environment:**
   ```bash
   # On macOS/Linux:
   source .venv/bin/activate
   
   # On Windows:
   .venv\Scripts\activate
   ```
<!-- END AUTO-GENERATED: setup -->

<!-- AUTO-GENERATED: how-to-run -->
## How to Run

**Using the Makefile:**
```bash
make run
```

**Using uvicorn directly:**
```bash
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`

- API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`
<!-- END AUTO-GENERATED: how-to-run -->

## Database Container Setup

### Starting the PostgreSQL Container with Podman

**Check if the container exists:**
```bash
podman ps -a | grep postgres-oc
```

**Start an existing container:**
```bash
podman start postgres-oc
```

**Create and start a new PostgreSQL container (if it doesn't exist):**
```bash
podman run -d \
  --name postgres-oc \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=fastapi_db \
  -p 5432:5432 \
  postgres:latest
```

**Verify the container is running:**
```bash
podman ps | grep postgres-oc
```

**Stop the container:**
```bash
podman stop postgres-oc
```

**View container logs:**
```bash
podman logs postgres-oc
```

### Using the Makefile

If you have database-related targets in your Makefile, you can also use:
```bash
make db-start    # Start database container
make db-stop     # Stop database container
```

<!-- AUTO-GENERATED: project-structure -->
## Project Structure

```
.
├── app/                    # Application package
│   ├── main.py            # FastAPI app instantiation and router setup
│   ├── routes/            # Route handlers
│   │   └── hello.py       # Hello world endpoint
│   └── models/            # Data models
├── requirements.txt       # Python dependencies
├── Makefile              # Helper commands
├── README.md             # This file
└── .gitignore            # Git ignore rules
```
<!-- END AUTO-GENERATED: project-structure -->

<!-- AUTO-GENERATED: dependencies -->
## Dependencies

- **fastapi** - Modern web framework for building APIs
- **uvicorn** - ASGI server for running FastAPI

View full list in `requirements.txt`
<!-- END AUTO-GENERATED: dependencies -->

<!-- AUTO-GENERATED: adding-routes -->
## Adding New Routes

1. Create a new file in `app/routes/` (e.g., `app/routes/users.py`):
   ```python
   from fastapi import APIRouter
   
   router = APIRouter()
   
   @router.get("/users")
   async def get_users():
       return {"users": []}
   ```

2. Import and include the router in `app/main.py`:
   ```python
   from app.routes import users
   app.include_router(users.router)
   ```
<!-- END AUTO-GENERATED: adding-routes -->
