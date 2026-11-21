# LLM Chatbot with Key Failover and Response Caching

A full-stack AI chatbot application built with **React + Vite** (frontend) and **Python FastAPI + LiteLLM** (backend), featuring automatic API key failover, response caching, multi-turn conversation state, and per-request token tracking — all stored in **SQLite**.

---

## 1. Live URLs

| Tier     | URL                                           |
| -------- | --------------------------------------------- |
| Frontend | `https://lyftr-ai-chatbot.vercel.app`         |
| Backend  | `https://lyftr-ai-chatbot.onrender.com`       |

> **Note:** Replace the placeholder URLs above with your actual deployment URLs after deploying.

---

## 2. Run locally: with Docker and without

### With Docker

```bash
# Clone the repo
git clone https://github.com/yourusername/lyftr-ai-chatbot.git
cd lyftr-ai-chatbot

# Configure environment
cp .env.example .env
# Edit .env with your real API keys (at least 2)

# Start both services
make up

# Frontend → http://localhost:3000
# Backend  → http://localhost:8000

# Stop
make down
```

### Without Docker

**Backend:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set env vars (or export them)
export LLM_API_KEYS="your-key-1,your-key-2"
export DATABASE_URL="sqlite:///./data/app.db"
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"
export ENABLE_FAILURE_SIMULATION=true

uvicorn app.main:app --reload --port 8000
```

**Frontend (new terminal):**

```bash
cd frontend
npm install

# Optional: set backend URL (defaults to http://localhost:8000)
export VITE_API_URL=http://localhost:8000

npm run dev
# → http://localhost:5173
```

**Run backend tests:**

```bash
cd backend
python3 -m pytest tests/ -v
```

---

## 3. Design decisions

### Key fallback

- API keys are configured via the `LLM_API_KEYS` env var (comma-separated). Each key gets an ID: `key_1`, `key_2`, etc.
- On every `/chat` request the backend iterates through the key pool sequentially. If a key returns HTTP 429 (rate limit), a quota error, or any 5xx status, it is skipped and the next key is tried.
- The number of skipped keys is reported as `fallback_attempts` in the response metadata.
- If **all** keys fail, the endpoint returns `503 {"detail": "all providers unavailable"}` and the failed message is **not** persisted to the session.

### Caching

- Uses **LiteLLM's built-in in-memory cache** (`litellm.cache = Cache(type="local")`).
- The cache key is derived from the **model + the full message list** (system prompt + history + new message), so the same first message in a new session will return `LLM_CACHE` on the second call.
- A cache hit returns the **identical reply text** with `resolution_source: "LLM_CACHE"`, `key_id: null`, `fallback_attempts: 0`, and significantly lower latency.

### SQLite session storage

- All conversation messages are stored in a SQLite `messages` table, keyed by `session_id`.
- The database file location is set via `DATABASE_URL` (default: `sqlite:////data/app.db`) and survives container restarts via a Docker named volume mounted at `/data`.
- The schema (table + index) is auto-created on application startup.
- The client sends only the new message; the backend reconstructs the full conversation from the DB before each LLM call.

---

## 4. Verification

### Failover

```bash
# Force key_1 to fail with 429 → backend falls back to key_2
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: key_1=429" \
  -d '{"session_id": "test-failover", "message": "Hello"}'
# → 200, metadata.key_id = "key_2", metadata.fallback_attempts = 1

# Force ALL keys to fail
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-Simulate-Failure: *=429" \
  -d '{"session_id": "test-all-fail", "message": "Hello"}'
# → 503, {"detail": "all providers unavailable"}
```

### Cache hits

```bash
# First call → LIVE_INFERENCE
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "cache-1", "message": "What is 2+2?"}'

# Same message in a NEW session → LLM_CACHE (identical reply, faster latency)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "cache-2", "message": "What is 2+2?"}'
```

### Per-message token usage

Each response includes `input_tokens` and `output_tokens` in the metadata. These are **per-request** counts (never a running total). The frontend displays them next to every assistant reply.

### Session history

```bash
curl http://localhost:8000/sessions/cache-1/messages
# Returns the full conversation for that session, oldest first
```

### Health check

```bash
curl http://localhost:8000/health
# → {"status": "ok", "keys_configured": 2, "cache_enabled": true}
```

---

## 5. Setup Used

- **Editor:** VS Code / Cursor with AI-assisted development
- **AI Tools:** Antigravity AI assistant for code generation and architecture
- **Backend:** Python 3.12, FastAPI, LiteLLM, aiosqlite, Pydantic v2
- **Frontend:** React 18, Vite, react-markdown
- **Infrastructure:** Docker, Docker Compose, nginx

---

## 6. Bonus features

- **System prompt customization:** An expandable text area at the top of the chat lets users set a custom system prompt per session. The prompt persists across turns within the same session.
- **Markdown rendering:** Assistant responses render Markdown (code blocks, lists, bold, etc.) using `react-markdown`.
- **Color-coded metadata badges:** `LIVE_INFERENCE` shows in green, `LLM_CACHE` in blue — making it instantly visible whether a response came from cache.
- **Responsive design:** The chat interface adapts to mobile and desktop viewports.
- **Typing indicator:** An animated indicator shows while waiting for the LLM response.
- **Comprehensive test suite:** 20 backend tests covering health, chat, validation, failover simulation, caching, multi-turn state, and session history.

---

## Repository structure

```
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI app, lifespan, CORS, error handlers
│   │   ├── config.py        # Settings from env vars
│   │   ├── database.py      # aiosqlite DB setup and queries
│   │   ├── models.py        # Pydantic request/response schemas
│   │   ├── routes.py        # /health, /chat, /sessions endpoints
│   │   ├── llm_service.py   # LiteLLM with key pool, failover, caching
│   │   └── utils.py         # Header parsing helpers
│   ├── tests/
│   │   ├── conftest.py      # Shared fixtures
│   │   ├── test_health.py
│   │   ├── test_chat.py
│   │   └── test_sessions.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx / App.css
│   │   ├── main.jsx / index.css
│   │   ├── components/       # ChatContainer, MessageInput, MessageList,
│   │   │                     # AssistantMessage, UserMessage, MetadataDisplay,
│   │   │                     # SystemPrompt (each with .jsx + .css)
│   │   └── utils/api.js      # API client
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── vite.config.js
│   └── package.json
├── docker-compose.yml
├── Makefile
├── .env.example
├── .gitignore
└── README.md
```

---

## Environment variables

| Variable                    | Required | Description                                           |
| --------------------------- | -------- | ----------------------------------------------------- |
| `LLM_API_KEYS`             | ✅       | Comma-separated API keys (at least 2)                 |
| `DATABASE_URL`              |          | SQLite path (default: `sqlite:////data/app.db`)       |
| `ALLOWED_ORIGINS`           |          | Comma-separated CORS origins                          |
| `ENABLE_FAILURE_SIMULATION` |          | Set to `true` to enable `X-Simulate-Failure` header   |
| `DEFAULT_MODEL`             |          | LiteLLM model name (default: `gemini/gemini-2.0-flash`) |
| `DEFAULT_SYSTEM_PROMPT`     |          | Default system prompt text                            |
| `VITE_API_URL`              |          | Backend URL for frontend (build-time, default: `http://localhost:8000`) |
