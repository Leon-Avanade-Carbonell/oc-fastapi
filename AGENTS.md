# oc-fastapi Project Rules

This is a FastAPI project using `uv` for Python package management and virtual environment handling.

## Package Installation

**CRITICAL: Always use `uv` for installing Python packages.** Never use `pip` directly.

### Installation Commands
- Always use: `uv pip install <package_name>`
- Never use: `pip install <package_name>`

When users ask to install packages, dependencies, or modules:
1. Use `uv pip install` for single packages
2. Use `uv pip install -r requirements.txt` for installing from requirements
3. Use `uv sync` to sync dependencies from pyproject.toml (if available)

### Example
```bash
# Correct - use uv
uv pip install psycopg2-binary

# Incorrect - do not use
pip install psycopg2-binary
```

## Project Structure
- `app/` - FastAPI application code
- `notebooks/` - Jupyter notebooks for analysis/prototyping
- `.venv/` - Virtual environment (managed by uv)
- `requirements.txt` - Python dependencies

## Development Standards
- Use Python with FastAPI framework
- Leverage uv's fast package installation and environment management
- When working with notebooks, remember to install packages via uv
