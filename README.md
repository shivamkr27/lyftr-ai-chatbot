# Lyftr AI Full-Stack Chatbot

## 1. Live URLs

The static frontend is deployed on GitHub Pages. The backend is running on the existing Oracle VM, with HTTPS and persistent SQLite storage. The VM's billing depends on the Oracle account's instance and storage terms; no new VM or paid hosting service was created.

- Frontend: [https://shivamkr27.github.io/lyftr-ai-chatbot/](https://shivamkr27.github.io/lyftr-ai-chatbot/)
- Backend API: [https://130.210.92.193.sslip.io](https://130.210.92.193.sslip.io)
- Backend health: [https://130.210.92.193.sslip.io/health](https://130.210.92.193.sslip.io/health)
- The API was verified with real Groq inference, cross-session cache hits, key fallback, HTTPS, and SQLite persistence across container recreation. The Pages workflow now defaults to this backend URL; the static site needs a successful workflow deployment of the latest commit to enable chat.
- The existing VM has a persistent Docker volume at `/data`, an automatically renewed Let's Encrypt certificate, and SSH restricted to the active client IP. HTTP/HTTPS are public; unused inbound ports 6443 and 12250 were removed.

### GitHub Pages frontend preparation

The static frontend is prepared for GitHub Pages by `.github/workflows/deploy-pages.yml` and `frontend/vite.config.js`. The workflow uses a repository-specific asset base path and publishes only `frontend/dist`; it does not host or package the FastAPI backend.

The workflow uses the repository Actions variable `VITE_API_BASE_URL` if set; otherwise it builds the frontend with the currently deployed backend URL. To change backend hosts later:

1. In **Settings → Pages**, keep the source set to **GitHub Actions**.
2. In **Settings → Secrets and variables → Actions → Variables**, set `VITE_API_BASE_URL` to the new public backend base URL (no trailing slash).
3. Ensure backend `ALLOWED_ORIGINS` includes the GitHub Pages origin.
4. Push to `main` or run **Deploy frontend to GitHub Pages** from the Actions tab.

If `VITE_API_BASE_URL` is unset, the workflow uses the current HTTPS API URL rather than localhost.

### Backend deployment preparation

The backend runs in Docker on the existing Oracle VM. Nginx terminates HTTPS and proxies to the backend bound to localhost; Docker stores SQLite in a named volume mounted at `/data`. The remote `.env` is root-readable only and is not in the repository. The configured LiteLLM model is `groq/openai/gpt-oss-120b`, corresponding to the `openai/gpt-oss-120b` model selected in the supplied Groq model list.

## 2. Run locally: with Docker and without

### Docker

The root `.env` contains local configuration and is ignored by Git. It must contain two valid Groq keys in `LLM_API_KEYS` and the selected LiteLLM model `groq/openai/gpt-oss-120b`. The second key is used for failover when the first key is rate-limited or unavailable. To prepare a fresh checkout:

```powershell
Copy-Item .env.example .env
# Replace the placeholder values locally; do not commit .env.
make up
```

Open `http://localhost:3001`. The API is available at `http://localhost:8001`.

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
$env:LLM_MODEL="groq/<account-accessible-model>"
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

- LiteLLM performs model calls and built-in local response caching. The complete system prompt, history, and new message form the cache context.
- Configure Groq models using LiteLLM's `groq/<model-id>` form. Groq model IDs containing a slash keep that slash, so the selected `openai/gpt-oss-120b` is configured as `groq/openai/gpt-oss-120b`.
- Groq model availability is listed in the [official supported models documentation](https://console.groq.com/docs/models).
- API keys are assigned key IDs in configuration order. Retryable HTTP 429, 500, 502, 503, and quota/rate-limit errors advance to the next key.
- Simulated failures apply only for the current request and never invalidate real credentials.
- SQLite stores ordered user and assistant messages under `session_id`. Assistant metadata is stored as JSON.
- The Docker setup mounts a named volume at `/data`, while `DATABASE_URL` selects `/data/app.db`.

## 4. Verification: how to see failover, cache hits and per-message token usage

Run the API:

```powershell
curl.exe http://localhost:8001/health

curl.exe -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d "{\"session_id\":\"s-cache-test\",\"message\":\"What is the capital of France?\"}"
curl.exe -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d "{\"session_id\":\"s-cache-test-2\",\"message\":\"What is the capital of France?\"}"
```

The second identical first message should return `LLM_CACHE` with a cache-preserved token count and `key_id: null`.

Failover:

```powershell
curl.exe -X POST http://localhost:8001/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: key_1=429" -d "{\"session_id\":\"s-failover\",\"message\":\"Explain resilience briefly.\"}"

curl.exe -X POST http://localhost:8001/chat -H "Content-Type: application/json" -H "X-Simulate-Failure: *=429" -d "{\"session_id\":\"s-failed\",\"message\":\"This request must fail.\"}"
```

Retrieve history:

```powershell
curl.exe http://localhost:8001/sessions/s-cache-test/messages
```

### Verification status

- Backend test suite: 17 passed using mocked provider responses.
- Frontend build passed locally and with the `/lyftr-ai-chatbot/` Pages base path. `npm audit` reported zero vulnerabilities.
- Local Docker Compose: frontend returns HTTP 200, backend health is `ok`, and both ports are bound to localhost.
- Live HTTPS inference returned `LIVE_INFERENCE` with model and per-message token metadata.
- Identical first messages in different sessions returned `LIVE_INFERENCE` then `LLM_CACHE`.
- Simulated first-key 429 used key 2 successfully with one fallback attempt. Simulated all-key failure returned HTTP 503 and created no history.
- SQLite history remained available after forcibly recreating the backend container; the named volume was retained.
- HTTPS certificate, HTTP-to-HTTPS redirect, and GitHub Pages CORS preflight were verified. The remaining release check is to deploy the latest frontend workflow and try chat from the public Pages site.

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
