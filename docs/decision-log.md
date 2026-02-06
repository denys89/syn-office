# Synoffice Decision Log

This document tracks all architectural and design decisions made during development.

---

## Decision #1: Technology Stack Selection

**Date:** 2026-01-21  
**Status:** Approved

### Context
Need to select the technology stack for Synoffice MVP.

### Decision
- **Frontend:** Next.js with TypeScript and Tailwind CSS
- **Backend API:** Go with Fiber framework
- **Agent Orchestrator:** Python with FastAPI
- **Database:** PostgreSQL + Redis + Qdrant
- **LLM Provider:** OpenAI
- **Authentication:** Simple JWT

### Rationale
- Go/Fiber provides high performance for REST + WebSocket
- Python/FastAPI is ideal for AI/ML workloads with asyncio
- Next.js offers excellent developer experience and SSR capabilities
- PostgreSQL for relational data, Redis for real-time, Qdrant for vector memory

---

## Decision #2: Multi-Service Architecture

**Date:** 2026-01-21  
**Status:** Approved

### Context
Deciding between monolith vs microservices for MVP.

### Decision
Three separate services:
1. Backend API (Go)
2. Agent Orchestrator (Python)
3. Frontend (Next.js)

### Rationale
- Separation allows each service to use the best language for its purpose
- Python ecosystem is better for AI/LLM work
- Go is better for high-performance API work
- Services communicate via HTTP and Redis pub/sub

---

## Decision #3: Initial Agent Roles

**Date:** 2026-01-21  
**Status:** Approved

### Context
Selecting which AI agent roles to implement for MVP.

### Decision
Four agent roles:
1. **Engineer** (Alex) - Coding, debugging, architecture
2. **Analyst** (Morgan) - Data analysis, reporting
3. **Writer** (Jordan) - Content creation, documentation
4. **Planner** (Sam) - Task management, scheduling

### Rationale
These four roles cover the most common office work scenarios and demonstrate the "AI as coworker" concept effectively.

---

## Decision #4: Deployment Strategy

**Date:** 2026-01-21  
**Status:** Approved

### Context
Deciding deployment target for MVP.

### Decision
Cloud deployment for MVP phase.

### Rationale
- Allows real-world testing
- Validates scalability assumptions
- Enables remote access for demos
