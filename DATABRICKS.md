# Running on Databricks

This guide covers deploying and running the FastAPI application in Databricks.

<!-- AUTO-GENERATED: databricks-setup -->
## Cluster Setup

### Requirements

- **Databricks Runtime**: 14.0 or later with Python 3.10+
- **Cluster type**: All-purpose or Job cluster
- **Minimum resources**: 2 workers, driver with 4GB+ memory

### Environment Configuration

1. **Create or configure a cluster** in your Databricks workspace
2. **Install dependencies** using one of the methods below:

#### Using pip (Standard)
```bash
pip install -r requirements.txt
```

#### Using uv (Faster alternative)
```bash
pip install uv
uv pip install -r requirements.txt
```

3. **Verify installation:**
   ```bash
   python -c "import fastapi; import uvicorn; print('Dependencies installed successfully')"
   ```
<!-- END AUTO-GENERATED: databricks-setup -->

<!-- AUTO-GENERATED: databricks-run-job -->
## Running as a Databricks Job

### Option 1: Run in a Job Cluster

1. **Create a new job** in Databricks
2. **Task type**: Python script
3. **Script path**: Upload or reference your FastAPI app

Create a file `run_server.py` in the project root:
```python
import subprocess
import sys

# Install dependencies
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"])

# Run the FastAPI server
subprocess.call([
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000"
])
```

4. **Configure the job** to run this script
5. **Monitor** the job run in the Databricks UI

### Option 2: Run in an All-Purpose Cluster (Interactive)

1. **Attach a notebook** to your cluster
2. **Install dependencies:**
   ```python
   %pip install -r requirements.txt
   ```

3. **Run the server:**
   ```python
   import subprocess
   subprocess.Popen([
       "python", "-m", "uvicorn",
       "app.main:app",
       "--host", "0.0.0.0",
       "--port", "8000"
   ])
   ```

4. **Access the server** at `http://<driver-ip>:8000`
<!-- END AUTO-GENERATED: databricks-run-job -->

<!-- AUTO-GENERATED: databricks-rest-endpoint -->
## Databricks REST Endpoint

### Exposing as a Databricks REST API Endpoint

1. **Create a Model Serving Endpoint** (if using Databricks Model Serving):
   - Deploy the FastAPI app as a containerized service
   - Reference the Docker image in the endpoint configuration

2. **Alternatively, use Databricks Jobs API**:
   - Create a job that runs the FastAPI server
   - Expose via Databricks API gateway

3. **Access the endpoint:**
   ```bash
   curl http://<databricks-instance>/api/2.0/endpoints/<endpoint-name>/
   ```

### Example: Query the hello-world endpoint from Databricks

```python
import requests

# Replace with your Databricks driver IP or hostname
BASE_URL = "http://<driver-ip>:8000"

response = requests.get(f"{BASE_URL}/")
print(response.json())  # Output: {"message": "Hello, World!"}
```
<!-- END AUTO-GENERATED: databricks-rest-endpoint -->

<!-- AUTO-GENERATED: databricks-notebook -->
## Testing from a Databricks Notebook

### Sample Notebook Code

Create a notebook in Databricks and run the following cells:

**Cell 1: Install dependencies**
```python
%pip install -r requirements.txt
```

**Cell 2: Start the FastAPI server (in background)**
```python
import subprocess
import time

# Start the server in a subprocess
proc = subprocess.Popen([
    "python", "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000"
])

# Wait for server to start
time.sleep(3)

print("Server started (PID: {})".format(proc.pid))
```

**Cell 3: Test the hello-world endpoint**
```python
import requests
import json

response = requests.get("http://localhost:8000/")
print(json.dumps(response.json(), indent=2))
```

**Cell 4: Check API documentation**
```python
# FastAPI auto-generates interactive docs
print("Swagger UI: http://<driver-ip>:8000/docs")
print("ReDoc: http://<driver-ip>:8000/redoc")
```

**Cell 5: Stop the server (optional)**
```python
import os
import signal

os.kill(proc.pid, signal.SIGTERM)
print("Server stopped")
```

### Testing Multiple Endpoints

```python
import requests

endpoints = [
    ("GET", "http://localhost:8000/", None),
]

for method, url, payload in endpoints:
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=payload)
        
        print(f"{method} {url}: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    except Exception as e:
        print(f"Error: {e}")
```
<!-- END AUTO-GENERATED: databricks-notebook -->

<!-- AUTO-GENERATED: databricks-troubleshooting -->
## Troubleshooting

### Dependency Installation Issues in Databricks
Use `--upgrade` flag when installing:
```bash
%pip install --upgrade -r requirements.txt
```

Or with uv:
```bash
pip install --upgrade uv
uv pip install -r requirements.txt
```

### Port Already in Use on Driver
If port 8000 is already in use:
```python
# Stop previous process
import subprocess
subprocess.call(["pkill", "-f", "uvicorn"])

# Wait and restart
import time
time.sleep(2)

# Then run your server again
```

### Network Access Issues
- Ensure the Databricks cluster allows outbound connections on port 8000
- Check Databricks workspace security group rules for internal communication
- Verify the driver IP is accessible from other cluster nodes
- Test connectivity: `curl http://<driver-ip>:8000/docs`

### Import Errors in Databricks Notebook
Ensure your project path is accessible:
```python
import sys
import os

# Add project to path if running from workspace
sys.path.insert(0, "/Workspace/your-project-path")
```

### Logging and Debugging in Databricks
Enable debug logging:
```python
%pip install -q python-json-logger

import subprocess
subprocess.call([
    "python", "-m", "uvicorn",
    "app.main:app",
    "--log-level", "debug",
    "--host", "0.0.0.0",
    "--port", "8000"
])
```

### Cluster Detach Issues
If the cluster detaches and stops your server:
1. Use a **Job cluster** instead of all-purpose cluster for persistent runs
2. Or implement a restart mechanism in your job script
3. Check Databricks job logs for cluster termination reasons
<!-- END AUTO-GENERATED: databricks-troubleshooting -->

## Additional Resources

- [Databricks documentation](https://docs.databricks.com/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Uvicorn documentation](https://www.uvicorn.org/)
- [uv package manager](https://docs.astral.sh/uv/)
