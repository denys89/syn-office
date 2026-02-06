# Synoffice - Quick Reference

## 🚀 Quick Start Commands

### Start Everything (Development)
```bash
# 1. Start infrastructure
cd infra && docker-compose up -d postgres redis qdrant

# 2. Start backend (in new terminal)
cd backend && go run .

# 3. Start orchestrator (in new terminal)
cd agent-orchestrator && pip install -e . && python main.py

# 4. Start frontend (in new terminal)
cd frontend && npm run dev
```

### Stop Everything
```bash
# Stop infrastructure
cd infra && docker-compose down

# Stop other services with Ctrl+C in their terminals
```

---

## 📡 Service URLs

| Service | URL | Health Check |
|---------|-----|--------------|
| Frontend | http://localhost:3000 | Open in browser |
| Backend API | http://localhost:8080 | http://localhost:8080/health |
| Orchestrator | http://localhost:8000 | http://localhost:8000/health |
| PostgreSQL | localhost:5432 | `docker exec -it synoffice-postgres pg_isready` |
| Redis | localhost:6379 | `docker exec -it synoffice-redis redis-cli ping` |
| Qdrant | http://localhost:6333 | http://localhost:6333/dashboard |

---

## 🔑 Environment Variables

**Required:**
- `OPENAI_API_KEY` - Your OpenAI API key

**Optional (have defaults):**
- `JWT_SECRET` - JWT signing secret
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `QDRANT_URL` - Qdrant connection

**Set in:** `infra/.env`

---

## 📁 Key Directories

```
synoffice/
├── backend/              # Go API
│   ├── api/             # HTTP handlers
│   ├── domain/          # Business entities
│   ├── service/         # Business logic
│   └── repository/      # Database access
├── agent-orchestrator/   # Python AI engine
├── frontend/            # Next.js UI
│   └── src/
│       ├── app/         # Pages
│       ├── components/  # React components
│       └── lib/         # Utilities
└── infra/               # Infrastructure
    ├── docker-compose.yml
    └── migrations/
```

---

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart PostgreSQL
cd infra && docker-compose restart postgres
```

### Backend Won't Start
```bash
# Download dependencies
cd backend && go mod tidy

# Check for port conflicts
netstat -ano | findstr :8080
```

### Frontend Build Errors
```bash
# Clear cache and reinstall
cd frontend
rm -rf .next node_modules
npm install
```

### Orchestrator Errors
```bash
# Reinstall dependencies
cd agent-orchestrator
pip install -e . --force-reinstall
```

---

## 🧪 Testing

### Test Backend
```bash
cd backend
go test ./...
```

### Test Frontend
```bash
cd frontend
npm test
```

### Manual API Testing
```bash
# Register user
curl -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","name":"Test User"}'

# Login
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

---

## 📊 Database Access

### Connect to PostgreSQL
```bash
docker exec -it synoffice-postgres psql -U synoffice -d synoffice
```

### Useful SQL Queries
```sql
-- List all tables
\dt

-- View agent templates
SELECT id, name, role FROM agent_templates;

-- View users
SELECT id, email, name FROM users;

-- View conversations
SELECT id, type, name FROM conversations;
```

---

## 🔄 Common Workflows

### Add a New Agent Template
1. Connect to database
2. Insert into `agent_templates` table
3. Restart backend to refresh cache

### Reset Database
```bash
cd infra
docker-compose down -v
docker-compose up -d postgres
# Database will be recreated with migrations
```

### View Logs
```bash
# Backend logs (if running in background)
docker logs synoffice-backend

# Database logs
docker logs synoffice-postgres

# Redis logs
docker logs synoffice-redis
```

---

## 🎯 Development Tips

1. **Hot Reload:**
   - Frontend: Automatic with `npm run dev`
   - Backend: Use `air` for hot reload (optional)
   - Orchestrator: Restart manually or use `uvicorn --reload`

2. **Code Quality:**
   - Go: `go fmt ./...` and `go vet ./...`
   - Python: `black .` and `ruff check .`
   - TypeScript: `npm run lint`

3. **Git Workflow:**
   - `.gitignore` is already configured
   - Don't commit `.env` files
   - Keep commits focused and atomic

---

## 📞 Support

For issues or questions:
1. Check `PROJECT_SUMMARY.md` for overview
2. Review `README.md` for setup details
3. Check `docs/decision-log.md` for architecture decisions
4. Review code comments in key files

---

**Happy coding! 🚀**
