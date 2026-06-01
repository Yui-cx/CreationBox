# CreationBox MVP

CreationBox is a React + FastAPI MVP for a public-account AI writing workspace. It upgrades the original static prototype into a runnable full-stack app with account/password auth, daily quota, SSE streaming generation, history records, PostgreSQL, Redis, and Docker Compose.

## Quick Start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080).

Default login:

```text
Username: admin
Password: admin
```

Registration is disabled in the MVP admin-only mode. The default admin user has unlimited generation quota.

The default real provider is DeepSeek. When the selected provider key is empty, the backend falls back to the mock provider so the full flow still works locally.

DeepSeek:

```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_MODEL_TEXT=deepseek-v4-flash
DEEPSEEK_THINKING_ENABLED=false
```

OpenRouter:

```env
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_MODEL_TEXT=deepseek/deepseek-v4-flash
OPENROUTER_HTTP_REFERER=https://your-site.example
OPENROUTER_APP_TITLE=CreationBox
```

Generic OpenAI-compatible endpoint:

```env
AI_PROVIDER=openai-compatible
AI_BASE_URL=https://your-provider.example/v1
AI_API_KEY=your-provider-key
AI_MODEL_TEXT=your-model-id
```

## Local Development

Backend:

```powershell
cd backend
pip install -e ".[test]"
uvicorn app.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## API Surface

- `POST /api/auth/register` disabled in admin-only mode
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/me`
- `POST /api/generations/stream`
- `GET /api/generations`
- `GET /api/generations/{id}`
- `DELETE /api/generations/{id}`
- `POST /api/generations/{id}/export-markdown`

## Notes

- The initial schema is created on FastAPI startup for MVP speed. Add Alembic migrations before production rollout.
- Link crawling and file parsing are intentionally not implemented in v1; links are passed to the model as text context.
- The UI preserves the prototype's workbench-first structure, dark mode, copy/export actions, and mobile tool switcher.
