# NetProbe Pi - API Reference

This document provides reference information for the NetProbe Pi API. The API allows you to interact with the system programmatically.

## Authentication

All API endpoints (except for login) require authentication using either:

1. Cookie-based authentication (for browser sessions)
2. JWT token authentication (for programmatic access)

### Obtaining a JWT Token

```
POST /api/login
```

**Request Body:**
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

### Using the JWT Token

Include the token in the `Authorization` header of your requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## System Status

### Get System Status

```
GET /api/status
```

**Response:**
```json
{
  "version": "0.1.0",
  "uptime": "1 day, 3 hours, 45 minutes",
  "interfaces": {
    "eth0": {
      "status": "up",
      "addresses": {
        "ipv4": {
          "address": "192.168.1.100",
          "netmask": "255.255.255.0"
        }
      }
    },
    "wlan0": {
      "status": "up",
      "addresses": {
        "ipv4": {
          "address": "192.168.4.1",
          "netmask": "255.255.255.0"
        }
      }
    }
  }
}
```

## Plugins

### List All Plugins

```
GET /api/plugins
```

**Response:**
```json
[
  {
    "name": "ip_info",
    "description": "Get IP address information",
    "version": "1.0.0",
    "author": "NetProbe",
    "category": "network",
    "tags": ["ip", "network"],
    "enabled": true,
    "built_in": true
  },
  {
    "name": "ping_test",
    "description": "Ping a host or IP address",
    "version": "1.0.0",
    "author": "NetProbe",
    "category": "network",
    "tags": ["ping", "network"],
    "enabled": true,
    "built_in": true
  }
]
```

### Get Plugin Details

```
GET /api/plugin/{plugin_name}
```

**Response:**
```json
{
  "name": "ping_test",
  "description": "Ping a host or IP address",
  "version": "1.0.0",
  "author": "NetProbe",
  "category": "network",
  "tags": ["ping", "network"],
  "enabled": true,
  "built_in": true,
  "parameters": [
    {
      "name": "host",
      "type": "string",
      "description": "Host or IP to ping",
      "required": true
    },
    {
      "name": "count",
      "type": "integer",
      "description": "Number of pings to send",
      "required": false,
      "default": 4
    }
  ],
  "permissions": ["network"],
  "status": "idle",
  "last_run": "2023-05-15T10:30:45Z"
}
```

### Run a Plugin

```
POST /api/plugin/{plugin_name}/run
```

**Request Body:**
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

### Get Plugin Run Status

```
GET /api/plugin/{plugin_name}/run/{run_id}
```

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "plugin": "ping_test",
  "status": "completed",
  "start_time": "2023-05-15T10:30:45Z",
  "end_time": "2023-05-15T10:30:50Z",
  "progress": 100,
  "result": {
    "packets_sent": 4,
    "packets_received": 4,
    "packet_loss": 0,
    "min_rtt": 15.2,
    "avg_rtt": 18.6,
    "max_rtt": 24.1
  }
}
```

### Upload a Plugin

```
POST /api/plugin/upload
```

This is a multipart form-data request where the plugin file is uploaded as `plugin_file`.

**Response:**
```json
{
  "message": "Plugin installed successfully",
  "plugin": {
    "name": "custom_plugin",
    "description": "A custom plugin",
    "version": "1.0.0",
    "author": "User",
    "category": "custom",
    "tags": ["custom"],
    "enabled": true,
    "built_in": false
  }
}
```

### Uninstall a Plugin

```
POST /api/plugin/{plugin_name}/uninstall
```

**Response:**
```json
{
  "message": "Plugin uninstalled successfully"
}
```

## Sequences

### List All Sequences

```
GET /api/sequences
```

**Response:**
```json
[
  {
    "name": "network_check",
    "description": "Basic network connectivity check",
    "plugins": [
      {
        "name": "ip_info",
        "parameters": {}
      },
      {
        "name": "ping_test",
        "parameters": {
          "host": "8.8.8.8",
          "count": 4
        }
      }
    ]
  }
]
```

### Create a Sequence

```
POST /api/sequences
```

**Request Body:**
```json
{
  "name": "network_check",
  "description": "Basic network connectivity check",
  "plugins": [
    {
      "name": "ip_info",
      "parameters": {}
    },
    {
      "name": "ping_test",
      "parameters": {
        "host": "8.8.8.8",
        "count": 4
      }
    }
  ]
}
```

**Response:**
```json
{
  "message": "Sequence created successfully",
  "sequence": {
    "name": "network_check",
    "description": "Basic network connectivity check",
    "plugins": [
      {
        "name": "ip_info",
        "parameters": {}
      },
      {
        "name": "ping_test",
        "parameters": {
          "host": "8.8.8.8",
          "count": 4
        }
      }
    ]
  }
}
```

### Update a Sequence

```
PUT /api/sequences/{sequence_name}
```

**Request Body:**
```json
{
  "description": "Updated network connectivity check",
  "plugins": [
    {
      "name": "ip_info",
      "parameters": {}
    },
    {
      "name": "ping_test",
      "parameters": {
        "host": "1.1.1.1",
        "count": 5
      }
    }
  ]
}
```

**Response:**
```json
{
  "message": "Sequence updated successfully",
  "sequence": {
    "name": "network_check",
    "description": "Updated network connectivity check",
    "plugins": [
      {
        "name": "ip_info",
        "parameters": {}
      },
      {
        "name": "ping_test",
        "parameters": {
          "host": "1.1.1.1",
          "count": 5
        }
      }
    ]
  }
}
```

### Delete a Sequence

```
DELETE /api/sequences/{sequence_name}
```

**Response:**
```json
{
  "message": "Sequence deleted successfully"
}
```

### Run a Sequence

```
POST /api/sequences/{sequence_name}/run
```

**Response:**
```json
{
  "message": "Sequence started",
  "run_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Logs

### Export Logs

```
GET /api/logs/export?days=7
```

The response is a binary ZIP file containing the logs.

Query Parameters:
- `days`: Number of days of logs to include (default: 7)

## Settings

### Get Settings

```
GET /api/settings
```

**Response:**
```json
{
  "network": {
    "interface": "eth0",
    "poll_interval": 5,
    "auto_run": true,
    "default_plugins": ["ip_info", "ping_test"],
    "monitor_method": "poll"
  },
  "security": {
    "allow_eth0_access": false,
    "session_timeout": 3600
  },
  "logging": {
    "log_level": "INFO",
    "max_logs": 100
  },
  "web": {
    "port": 80,
    "host": "0.0.0.0"
  }
}
```

### Update Settings

```
POST /api/settings
```

**Request Body:**
```json
{
  "network": {
    "interface": "eth0",
    "poll_interval": 10,
    "auto_run": true
  },
  "security": {
    "allow_eth0_access": true
  }
}
```

**Response:**
```json
{
  "message": "Settings updated successfully"
}
```

### Change Password

```
POST /api/settings/password
```

**Request Body:**
```json
{
  "current_password": "old_password",
  "new_password": "new_password"
}
```

**Response:**
```json
{
  "message": "Password changed successfully"
}
```

## Error Responses

All API endpoints return standard HTTP status codes:

- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 500: Internal Server Error

Error responses include a JSON object with an error message:

```json
{
  "error": "Plugin not found: unknown_plugin"
}
```
