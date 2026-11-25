# Lyftr AI Full-Stack Chatbot

## 1. Live URLs

Live URLs will be added only after deployment is verified. Public deployment has not been performed: no hosting target has yet been confirmed to provide both a ₹0 backend and persistent mounted storage for SQLite.

- Render documents that free web services cannot attach persistent disks: [Render storage/pricing information](https://render.com/articles/how-much-does-cloud-application-hosting-cost-for-small-businesses).
- Hugging Face Spaces documents its default disk as non-persistent: [Spaces overview](https://huggingface.co/docs/hub/spaces-overview).
- Fly.io lists usage-based charges and a monthly credit requiring a payment card: [Fly.io pricing](https://fly.io/pricing/). It is not treated as guaranteed ₹0 hosting.

No live URL is claimed. Re-evaluate the hosting terms before deploying if the free-tier/storage conditions change.

- Frontend: Not yet deployed
- Backend: Not yet deployed

### GitHub Pages frontend preparation

The static frontend is prepared for GitHub Pages by `.github/workflows/deploy-pages.yml` and `frontend/vite.config.js`. The workflow uses a repository-specific asset base path and publishes only `frontend/dist`; it does not host or package the FastAPI backend.

After pushing this project to a GitHub repository:

1. In **Settings → Pages**, set the source to **GitHub Actions**.
2. In **Settings → Secrets and variables → Actions → Variables**, add `VITE_API_BASE_URL` with the public backend base URL (no trailing slash required).
3. Ensure the backend's `ALLOWED_ORIGINS` includes the GitHub Pages site origin and that its persistent volume is mounted at `/data`.
4. Push to `main` or run **Deploy frontend to GitHub Pages** from the Actions tab.

The workflow intentionally fails if `VITE_API_BASE_URL` is unset, rather than publishing a frontend that points to localhost.
The expected project-site URL is `https://shivamkr27.github.io/lyftr-ai-chatbot/` after a successful Pages deployment; this URL is not live or verified yet.

### Backend deployment preparation

The backend is independently containerized in `backend/Dockerfile`. Deploy that image only to a host that supports a persistent volume mounted at `/data`, and configure `LLM_API_KEYS`, `DATABASE_URL=sqlite:////data/app.db`, `ALLOWED_ORIGINS`, `ENABLE_FAILURE_SIMULATION=true`, `LLM_MODEL=groq/llama-3.3-70b-versatile`, and `CACHE_ENABLED=true` as backend environment variables. Store `LLM_API_KEYS` as a backend secret. Do not use an ephemeral filesystem for SQLite. No public backend deployment is configured or claimed until a no-cost persistent-volume host is confirmed.

## 2. Run locally: with Docker and without

### Docker

The root `.env` contains local configuration and is ignored by Git. It must contain two Groq keys in `LLM_API_KEYS` and the LiteLLM model `groq/llama-3.3-70b-versatile`. To prepare a fresh checkout:

```powershell
Copy-Item .env.example .env
# Replace the placeholder values locally; do not commit .env.
make up
```

Open `http://localhost:3000`. The API is available at `http://localhost:8000`.

Stop and remove containers:

```powershell
make down
```

The `lyftr_data` named volume persists SQLite at `/data/app.db`.

### Without Docker

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LLM_API_KEYS="key_1_value,key_2_value"
$env:DATABASE_URL="sqlite:///D:/sem7/spm project/lyftr-ai-chatbot/app.db"
$env:ALLOWED_ORIGINS="http://localhost:5173"
$env:ENABLE_FAILURE_SIMULATION="true"
$env:LLM_MODEL="groq/llama-3.3-70b-versatile"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```powershell
cd frontend
npm install
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev -- --port 5173
```

## 3. Design decisions: key fallback, caching, SQLite session storage

- LiteLLM performs real model calls and built-in local response caching. The complete system prompt, history, and new message form the cache context.
- Groq inference uses LiteLLM's `groq/llama-3.3-70b-versatile` model identifier.
- Groq model availability is listed in the [official supported models documentation](https://console.groq.com/docs/models).
- API keys are assigned key IDs in configuration order. Retryable HTTP 429, 500, 502, 503, and quota/rate-limit errors advance to the next key.
- Simulated failures apply only for the current request and never invalidate real credentials.
- SQLite stores ordered user and assistant messages under `session_id`. Assistant metadata is stored as JSON.
- The Docker setup mounts a named volume at `/data`, while `DATABASE_URL` selects `/data/app.db`.

## 4. Verification: how to see failover, cache hits and per-message token usage

Run the API:

```powershell
curl.exe http://localhost:8000/health

curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"session_id\":\"s-cache-test\",\"message\":\"What is the capital of France?\"}"
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"session_id\":\"s-cache-test-2\",\"message\":\"What is the capital of France?\"}"
```

The second identical first message should return `LLM_CACHE` with a cache-preserved token count and `key_id: null`.

Failover:

```powershell
curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=429" -d "{\"session_id\":\"s-failover\",\"message\":\"Explain resilience briefly.\"}"

curl.exe -X POST http://localhost:8000/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: *=429" -d "{\"session_id\":\"s-failed\",\"message\":\"This request must fail.\"}"
```

Retrieve history:

```powershell
curl.exe http://localhost:8000/sessions/s-cache-test/messages
```

### Verification status (local)

- Backend test suite: 13 passed using mocked provider responses; these are not real Groq inference tests.
- Frontend build passed locally and with the `/lyftr-ai-chatbot/` Pages base path. `npm audit` reported zero vulnerabilities.
- Docker Compose started both services; `/health` returned `ok` and the frontend returned HTTP 200.
- SQLite persistence was verified across container recreation using a temporary seeded fixture and the history endpoint. The fixture was removed afterward.
- The all-keys simulated failure returned HTTP 503 and did not add session history. Partial key-1 fallback is verified in mocked tests only.
- Real Groq requests from the host and backend container were blocked by Cloudflare with HTTP 403 / error 1010. Therefore real inference, real cache hits/token reuse, and real provider failover remain unverified.

## 5. Setup Used: your editor and AI tools

- Editor: Visual Studio Code
- Backend: Python, FastAPI, LiteLLM, SQLite
- Frontend: React, Vite
- Containers: Docker Compose and Make
- AI assistance: GitHub Copilot

## 6. Bonus features (if any)

- Optional per-session system prompt control
- Professional responsive chat layout
- Indexed SQLite message retrieval

## API contract

The application exposes exactly:

- `GET /health`
- `POST /chat`
- `GET /sessions/{session_id}/messages`

Run backend tests:

```powershell
cd backend
python -m pytest -q
```

## Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `LLM_API_KEYS` | Yes | Comma-separated API key pool; at least two |
| `DATABASE_URL` | Yes | SQLite URL |
| `ALLOWED_ORIGINS` | Yes | Comma-separated CORS origins |
| `ENABLE_FAILURE_SIMULATION` | Yes | Enables the `X-Simulate-Failure` header |
| `LLM_MODEL` | No | LiteLLM model name |
| `CACHE_ENABLED` | No | Enables LiteLLM local cache |
| `VITE_API_BASE_URL` | Frontend build | Public backend URL |

Never commit real credentials.
