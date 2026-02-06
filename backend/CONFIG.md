# Backend Configuration

This backend uses [`github.com/kelseyhightower/envconfig`](https://github.com/kelseyhightower/envconfig) for configuration management.

## Configuration Files

- **`config/config.go`**: Centralized configuration struct with all settings
- **`.env.example`**: Example environment variables file

## Environment Variables

All configuration is loaded from environment variables. You can set these in:
- System environment variables
- `.env` file (create from `.env.example`)
- Container orchestration (Docker, Kubernetes, etc.)

### Available Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgres://synoffice:synoffice_secret@localhost:5432/synoffice?sslmode=disable` | PostgreSQL connection string |
| `JWT_SECRET` | `your-super-secret-jwt-key-change-in-production` | Secret key for JWT token signing |
| `ORCHESTRATOR_URL` | `http://localhost:8000` | URL of the agent orchestrator service |
| `INTERNAL_API_KEY` | `dev-internal-key-change-in-production` | API key for internal service-to-service communication |
| `BACKEND_PORT` | `8080` | Port for the backend server |
| `ENVIRONMENT` | `development` | Environment name (development, staging, production) |

## Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values:**
   ```bash
   # Update the values as needed
   nano .env
   ```

3. **Run the application:**
   ```bash
   go run main.go
   ```

## Production Deployment

⚠️ **Important**: For production deployments, make sure to:

1. **Change all default secrets:**
   - Set a strong `JWT_SECRET`
   - Set a strong `INTERNAL_API_KEY` (must match the orchestrator)
   
2. **Use secure database connections:**
   - Enable SSL/TLS (`sslmode=require`)
   - Use strong database passwords

3. **Set appropriate environment:**
   ```bash
   ENVIRONMENT=production
   ```

## Internal API Key

The `INTERNAL_API_KEY` is used for service-to-service authentication between the backend and the agent orchestrator. This key must match in both services:

- **Backend**: Set in `INTERNAL_API_KEY` environment variable
- **Orchestrator**: Set in `INTERNAL_API_KEY` in the orchestrator's `.env` file

This prevents unauthorized services from calling internal endpoints like `/api/v1/internal/task-complete`.

## Configuration Loading

The configuration is loaded using the `config.MustLoad()` function in `main.go`:

```go
cfg := config.MustLoad()
```

This function:
1. Reads environment variables
2. Falls back to default values if not set
3. Logs the loaded configuration
4. Panics if required variables are missing or invalid

## Adding New Configuration

To add a new configuration variable:

1. **Add to the `Config` struct in `config/config.go`:**
   ```go
   type Config struct {
       // ... existing fields
       NewSetting string `envconfig:"NEW_SETTING" default:"default_value"`
   }
   ```

2. **Add to `.env.example`:**
   ```bash
   # Description of the new setting
   NEW_SETTING=default_value
   ```

3. **Use in your code:**
   ```go
   cfg := config.MustLoad()
   value := cfg.NewSetting
   ```
