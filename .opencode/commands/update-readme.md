---
description: Update README and DATABRICKS documentation
agent: build
---

Analyze the FastAPI project structure and update both README.md and DATABRICKS.md files.

## For README.md

Scan:
1. `app/routes/` to discover all route handlers and their endpoints
2. `app/models/` to list any data models
3. `requirements.txt` to extract dependencies

Update the README.md sections marked with `<!-- AUTO-GENERATED: ... -->` comments:
- **setup**: Installation and venv setup instructions (with both pip and uv options)
- **how-to-run**: How to run the application
- **project-structure**: Tree of the project directory
- **dependencies**: List of dependencies with descriptions
- **adding-routes**: Instructions on how to add new routes

## For DATABRICKS.md

Update the DATABRICKS.md sections marked with `<!-- AUTO-GENERATED: ... -->` comments:
- **databricks-setup**: Cluster setup and dependency installation
- **databricks-run-job**: How to run as a Databricks job
- **databricks-rest-endpoint**: Exposing as REST endpoint
- **databricks-notebook**: Sample notebook code for testing
- **databricks-troubleshooting**: Common issues and solutions

## General Instructions

Preserve all content outside the AUTO-GENERATED markers. Only regenerate the marked sections.

If either file does not exist, create it from scratch with all standard sections.

Ensure all code examples and paths are consistent with the current project structure.
