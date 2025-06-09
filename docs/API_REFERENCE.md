# NetScout-Pi API Reference

This guide provides essential information for interacting with the NetScout-Pi API.

## Authentication

Get an API token:

```
POST /api/login
```

**Request:**
```json
{
  "password": "your_admin_password"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires": 3600
}
```

Use the token in all requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Common API Endpoints

### Get System Status
```
GET /api/status
```

### List All Plugins
```
GET /api/plugins
```

### Run a Plugin
```
POST /api/plugin/{plugin_name}/run
```

**Request:**
```json
{
  "host": "google.com",
  "count": 4
}
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running"
}
```

### Get Test Results
```
GET /api/plugin/{plugin_name}/run/{run_id}
```

### Export Logs
```
GET /api/logs/export?days=7
```

### Update Settings
```
POST /api/settings
```

**Request:**
```json
{
  "network": {
    "interface": "eth0",
    "poll_interval": 10
  }
}
```

## Automated Testing Example

This Python script demonstrates how to use the API for automated testing:

```python
import requests
import json
import time

# Configuration
API_URL = "http://netscout.local/api"
PASSWORD = "your_password"

# Login and get token
response = requests.post(f"{API_URL}/login", json={"password": PASSWORD})
token = response.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Run ping test
ping_params = {"host": "google.com", "count": 4}
response = requests.post(f"{API_URL}/plugin/ping_test/run", 
                         json=ping_params, headers=headers)
run_id = response.json()["run_id"]

# Wait for test to complete
while True:
    response = requests.get(f"{API_URL}/plugin/ping_test/run/{run_id}", 
                           headers=headers)
    status = response.json()["status"]
    if status != "running":
        break
    time.sleep(1)

# Get results
results = response.json()["result"]
print(f"Ping results: {json.dumps(results, indent=2)}")
```
