# 🚀 Synoffice - Step-by-Step Startup Guide

## Prerequisites Check

Before starting, make sure you have:
- ✅ Docker Desktop installed and running
- ✅ Go 1.21+ installed
- ✅ Python 3.11+ installed
- ✅ Node.js 20+ installed
- ✅ OpenAI API key

---

## Step 1: Configure Environment

```powershell
# Navigate to project root
cd c:\Users\denys\go\src\github.com\denys89\syn-office

# Copy environment template
cp infra\.env.example infra\.env

# Edit infra\.env and add your OpenAI API key
notepad infra\.env
```

**Add this line to `.env`:**
```
OPENAI_API_KEY=sk-your-actual-openai-key-here
```

---

## Step 2: Start Infrastructure (Docker)

```powershell
cd infra
docker-compose up -d postgres redis qdrant
```

**Wait ~10 seconds for services to start**, then verify:
```powershell
docker ps
```

You should see 3 containers running:
- `synoffice-postgres`
- `synoffice-redis`
- `synoffice-qdrant`

---

## Step 3: Start Backend (Go) - Terminal 1

```powershell
cd ..\backend
go run .
```

**Expected output:**
```
Connected to database
Starting server on port 8080
```

**Test it:**
Open http://localhost:8080/health in your browser
Should return: `{"status":"ok"}`

---

## Step 4: Start Orchestrator (Python) - Terminal 2

**Open a NEW terminal window**, then:

```powershell
cd c:\Users\denys\go\src\github.com\denys89\syn-office\agent-orchestrator

# Set environment variable (temporary for this session)
$env:OPENAI_API_KEY="sk-your-actual-key-here"

# Or load from .env file
$env:OPENAI_API_KEY=(Get-Content ..\infra\.env | Select-String "OPENAI_API_KEY" | ForEach-Object { $_.ToString().Split('=')[1] })

# Start the orchestrator
python main.py
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Database connected
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Test it:**
Open http://localhost:8000/health
Should return: `{"status":"ok","service":"orchestrator"}`

---

## Step 5: Start Frontend (Next.js) - Terminal 3

**Open another NEW terminal window**, then:

```powershell
cd c:\Users\denys\go\src\github.com\denys89\syn-office\frontend
npm run dev
```

**Expected output:**
```
▲ Next.js 16.1.4
- Local:        http://localhost:3000
```

---

## Step 6: Open the Application

🎉 **Open your browser and navigate to:**
http://localhost:3000

You should see the Synoffice landing page!

---

## Quick Test Flow

1. **Register a new account**
   - Click "Register"
   - Enter email, password, and name
   - Click "Create Your Office"

2. **Select AI Agents**
   - Choose at least one agent (Alex, Morgan, Jordan, or Sam)
   - Click "Continue"

3. **Start Chatting**
   - Click on an agent in the sidebar
   - Type a message and press Enter
   - Wait for the AI agent to respond!

---

## Troubleshooting

### "Cannot connect to database"
```powershell
# Check if PostgreSQL is running
docker ps | findstr postgres

# If not running, start it
cd infra
docker-compose up -d postgres
```

### "Module not found" (Python)
```powershell
cd agent-orchestrator
pip install -r requirements.txt
```

### "Port already in use"
```powershell
# Find what's using the port (e.g., 8080)
netstat -ano | findstr :8080

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### Backend won't start
```powershell
cd backend
go mod tidy
go run .
```

---

## Stopping Everything

### Stop Frontend/Backend/Orchestrator
Press `Ctrl+C` in each terminal window

### Stop Infrastructure
```powershell
cd infra
docker-compose down
```

---

## Environment Variables Reference

Create `infra\.env` with:

```env
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional (have defaults)
JWT_SECRET=your-super-secret-jwt-key-change-in-production
DATABASE_URL=postgres://synoffice:synoffice_secret@localhost:5432/synoffice?sslmode=disable
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
BACKEND_PORT=8080
```

---

## Service Health Checks

| Service | URL | Expected Response |
|---------|-----|-------------------|
| Backend | http://localhost:8080/health | `{"status":"ok"}` |
| Orchestrator | http://localhost:8000/health | `{"status":"ok","service":"orchestrator"}` |
| Frontend | http://localhost:3000 | Landing page |
| PostgreSQL | `docker exec -it synoffice-postgres pg_isready` | `accepting connections` |
| Redis | `docker exec -it synoffice-redis redis-cli ping` | `PONG` |

---

**You're all set! Happy chatting with your AI employees! 🎊**
