---
description: Start the Synoffice development environment
---

# Starting Synoffice Development Environment

Follow these steps to run Synoffice locally:

## 1. Start Infrastructure

// turbo
```bash
cd infra && docker-compose up -d postgres redis qdrant
```

Wait for services to be healthy (~10 seconds).

## 2. Start Backend API (Go)

```bash
cd backend && go mod tidy && go run .
```

Backend will be available at http://localhost:8080

## 3. Start Agent Orchestrator (Python)

```bash
cd agent-orchestrator && pip install -r requirements.txt && python main.py
```

Orchestrator will be available at http://localhost:8000

## 4. Start Frontend (Next.js)

```bash
cd frontend && npm run dev
```

Frontend will be available at http://localhost:3000

## Quick Health Checks

// turbo
```bash
curl http://localhost:8080/health
curl http://localhost:8000/health
```

## Stop All Services

```bash
cd infra && docker-compose down
```
