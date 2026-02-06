# Synoffice – AI-Native Digital Office

Synoffice is an AI-native digital office where a human user (the **Boss**) manages and collaborates with multiple **AI Agent Employees** through a chat-based interface.

## 🏗️ Architecture

The project consists of three main services:

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **Backend API** | Go / Fiber | 8080 | REST + WebSocket API |
| **Agent Orchestrator** | Python / FastAPI | 8000 | AI agent execution engine |
| **Frontend** | Next.js / TypeScript | 3000 | Chat-based UI |

### Data Layer
- **PostgreSQL** - Primary database
- **Redis** - Pub/sub and caching
- **Qdrant** - Vector memory for agents

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Go 1.21+ (for local backend development)
- Python 3.11+ (for local orchestrator development)
- Node.js 20+ (for local frontend development)
- OpenAI API Key

### 1. Clone and Setup

```bash
cd syn-office

# Copy environment file
cp infra/.env.example infra/.env

# Edit .env and add your OpenAI API key
```

### 2. Start Infrastructure (Database, Redis, Qdrant)

```bash
cd infra
docker-compose up -d postgres redis qdrant
```

### 3. Run Migrations

The migrations run automatically when PostgreSQL starts, but you can also run them manually:

```bash
docker exec -it synoffice-postgres psql -U synoffice -d synoffice -f /docker-entrypoint-initdb.d/001_initial_schema.sql
```

### 4. Start Backend (Go)

```bash
cd backend
go mod tidy
go run .
```

### 5. Start Orchestrator (Python)

```bash
cd agent-orchestrator
pip install -e .
python main.py
```

### 6. Start Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

### 7. Access the Application

Open http://localhost:3000 in your browser.

## 📁 Project Structure

```
synoffice/
├── frontend/                 # Next.js App
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   ├── contexts/        # React contexts
│   │   └── lib/            # Utilities & API client
│   └── ...
├── backend/
│   ├── api/                 # HTTP / WebSocket handlers
│   ├── domain/              # Business entities & interfaces
│   ├── service/             # Use cases
│   ├── repository/          # Database access
│   └── main.go
├── agent-orchestrator/      # Python/FastAPI
│   ├── main.py             # FastAPI app
│   ├── orchestrator.py     # Task execution
│   ├── llm_client.py       # OpenAI integration
│   └── database.py         # Database access
├── infra/
│   ├── docker-compose.yml  # Infrastructure setup
│   └── migrations/         # Database migrations
└── docs/
    └── decision-log.md     # Architectural decisions
```

## 🤖 AI Agents

The MVP includes four AI agent roles:

| Agent | Role | Skills |
|-------|------|--------|
| **Alex** | Engineer | Coding, debugging, architecture |
| **Morgan** | Analyst | Data analysis, reporting, statistics |
| **Jordan** | Writer | Content creation, editing, documentation |
| **Sam** | Planner | Task management, scheduling, coordination |

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user

### Agents
- `GET /api/v1/agents/templates` - List agent templates
- `POST /api/v1/agents/select` - Select an agent
- `POST /api/v1/agents/select-multiple` - Select multiple agents
- `GET /api/v1/agents` - List office agents

### Conversations
- `GET /api/v1/conversations` - List conversations
- `POST /api/v1/conversations` - Create conversation
- `GET /api/v1/conversations/:id` - Get conversation
- `GET /api/v1/conversations/:id/messages` - Get messages
- `POST /api/v1/conversations/:id/messages` - Send message

### WebSocket
- `WS /ws?token=<jwt>` - Real-time connection

## 🔧 Development

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `JWT_SECRET` | JWT signing secret | Required in production |
| `DATABASE_URL` | PostgreSQL connection string | See .env.example |
| `REDIS_URL` | Redis connection string | redis://localhost:6379 |
| `QDRANT_URL` | Qdrant connection string | http://localhost:6333 |

### Running Tests

```bash
# Backend
cd backend && go test ./...

# Orchestrator
cd agent-orchestrator && pytest

# Frontend
cd frontend && npm test
```

## 📝 License

MIT License - See LICENSE file for details.

---

**Synoffice MVP** – Building the future of AI-native work.
