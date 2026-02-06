# Synoffice — AI Coding Guidelines

This document is a **working contract** between you (Founder / CTO) and any AI Code Editor you use.
All AI-generated code **MUST** comply with the rules defined here.

If there is any conflict between AI output and this document, **this document prevails**.

---

## 1. Purpose of This Document

- Maintain architectural consistency
- Prevent over-engineering
- Avoid spaghetti code
- Ensure Synoffice remains scalable and maintainable

AI **does not have full business context**.
AI **only executes narrowly defined technical instructions**.

---

## 2. Core Principles (NON-NEGOTIABLE)

1. **Design first, code second**
2. **One module = one responsibility**
3. **No AI logic inside gateway / controller layers**
4. **No business assumptions unless explicitly instructed**
5. **Less code, correctly written, is better than more code**

---

## 3. Mandatory Tech Stack

### Frontend
- Language: TypeScript
- Framework: Next.js (App Router)
- Styling: Tailwind CSS
- State Management: Zustand (only if necessary)
- Realtime: Native WebSocket

### Backend API
- Language: Go (Golang)
- Framework: Fiber
- Architecture: Clean Architecture (layered)

### Agent Orchestrator
- Language: Python
- Framework: FastAPI
- Async Model: asyncio

### Database
- PostgreSQL (primary database)
- Redis (cache, pub/sub, locking)
- Qdrant (vector memory)

### Infrastructure
- Docker for all services
- No new infrastructure components without explicit approval

---

## 4. Repository Structure (FINAL)

AI **MUST NOT** modify this structure.

```
synoffice/
├── frontend/
├── backend/
│   ├── api/            # HTTP / WebSocket handlers
│   ├── domain/         # Business entities & interfaces
│   ├── service/        # Use cases
│   ├── repository/     # Database access
│   ├── transport/      # External adapters
│   └── main.go
├── agent-orchestrator/
├── infra/
└── docs/
```

---

## 5. Backend Coding Rules (Go)

### DO
- Use interfaces for dependencies
- Return errors explicitly
- Use `context.Context`
- Apply structured logging

### DO NOT
- Do not query the database directly from handlers
- Do not place business logic in routers
- Do not use global state
- Do not introduce new frameworks or ORMs

Correct flow:
```
Handler → Service → Repository
```

---

## 6. Frontend Coding Rules

### DO
- Keep components small and reusable
- Separate UI from business logic
- Centralize state only when necessary

### DO NOT
- Do not fetch the same data from multiple places
- Do not store tokens in localStorage without justification
- Do not tightly couple UI to AI responses

---

## 7. Realtime & WebSocket Rules

- WebSocket is only responsible for:
  - Sending events
  - Receiving events
- No AI or business logic inside WebSocket handlers
- Every message **must** include an `event_id`

---

## 8. AI / Agent Rules (CRITICAL)

AI Code Editors **MUST NOT**:
- Modify system prompts
- Invent agent behaviors
- Merge multiple agent roles into one

Agents may only:
- Respond according to their assigned role
- Follow the defined autonomy level

---

## 9. Database Rules

- Every table **MUST** include `office_id`
- No cross-office queries
- All migrations must be backward-compatible

---

## 10. Prompting Rules for AI Code Editors

Every coding request must explicitly:
1. Specify the target file
2. Specify the function or responsibility
3. State what the AI **MUST NOT** do

Example of a correct prompt:

> "Create a WebSocket handler in Go for event `chat.message.send`. Persist the message to the database and publish it to Redis. Do not add any AI logic or additional business rules."

---

## 11. Definition of Done (MANDATORY)

A feature is considered DONE only if:
- The project builds successfully
- No runtime panics occur
- Errors are handled explicitly
- The feature can be tested manually end-to-end

If **any** condition fails → the feature is **NOT DONE**.

---

## 12. Change Management

- Any architectural change must:
  - Be discussed first
  - Be documented in `/docs/decision-log.md`

AI **MUST NOT** perform silent architectural changes.

---

## 13. Final Principle

AI is a **tool**, not a decision maker.

You are the:
- Architect
- Direction setter
- Vision holder

When in doubt → **ask, do not assume**.

---

**This document is FINAL for the MVP phase of Synoffice.**

