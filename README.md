# PaperIntel AI

PaperIntel AI is a deterministic research-paper analysis system. It extracts a PDF into a structured paper representation, builds an evidence-backed knowledge base, reasons over controlled rules, verifies propositional claims, evaluates publication requirements as a CSP, and searches hypothetical improvement plans. It does not use machine learning, LLMs, or external AI APIs.

## Architecture

The backend is a FastAPI application in `backend/`; the frontend is a React/Vite application in `frontend/`.

| Module | Responsibility | Implementation |
| --- | --- | --- |
| 1 | Repository scope | No standalone Module 1 component is represented in the current codebase. |
| 2 | PDF processing | Deterministic PDF parsing into a structured document; uploads remain in memory. |
| 3 | Knowledge representation | Entity, relationship, fact, and evidence graph construction. |
| 4 | Reasoning | Generic forward fixed-point chaining and goal-driven backward chaining over facts and rules. |
| 5 | Logical verification | Structured propositional formulas, truth-model checking, CNF conversion, resolution, and consistency checking. |
| 6 | Compliance | Data-defined CSP variables and constraints with propagation, forward checking, backtracking, and MRV. |
| 7 | Improvement planning | Immutable states, declarative actions, Uniform-Cost Search, and A* graph search. |
| 8 | Integrated analysis | Explainable orchestration of Modules 3-7, including evidence, traces, partial results, and cross-module checks. |
| 9 | System evaluation | Small, maintained deterministic benchmarks with runtime-measured results. |
| 10 | Production readiness | Configuration, safe errors, structured logging, deployment guidance, and architecture validation. |

The publication-specific rules, profiles, and suggested actions are controlled data supplied to generic engines. They are not replacements for the underlying reasoning, CSP, logic, or search algorithms.

## Prerequisites

- Python 3.11 or later
- Node.js 18 or later
- npm
- MongoDB only if a future persistence feature requires it; the current analysis pipeline runs without it

## Backend setup and run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --host 127.0.0.1 --port 8000
```

The health endpoint is available at `GET /health`. In development, interactive API documentation is available at `/docs` unless disabled by configuration.

## Frontend setup and run

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`. The frontend defaults to `http://localhost:8000` and can be pointed at another API using `VITE_API_BASE_URL`.

## Environment variables

Copy `backend/.env.example` and `frontend/.env.example`; never commit the resulting `.env` files.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Runtime mode: `development`, `testing`, or `production`. |
| `LOG_LEVEL` | `INFO` | Structured application log level. |
| `ENABLE_API_DOCS` | `true` outside production | Enables `/docs` and `/redoc`; set `false` for public production deployments. |
| `MAX_UPLOAD_SIZE_MB` | `20` | PDF upload limit, constrained to 1-100 MB. |
| `FRONTEND_ORIGINS` | local Vite origins | Comma-separated CORS allow-list. |
| `MONGO_URI` | unset | Optional MongoDB connection string. Do not place credentials in source control. |
| `DATABASE_NAME` | `paperintel_ai` | Optional MongoDB database name. |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend API base URL. |

When `MONGO_URI` is absent, `GET /health/database` safely returns `503` with `not configured`; no core module depends on MongoDB.

## Key API endpoints

| Endpoint | Purpose |
| --- | --- |
| `POST /api/papers/process` | Validate and parse one PDF held in memory. |
| `POST /api/papers/knowledge-base` | Build the Module 3 knowledge base. |
| `POST /api/reasoning/forward` / `backward` | Run Module 4 reasoning. |
| `POST /api/logic/model-check`, `resolution`, `consistency` | Run Module 5 verification. |
| `POST /api/compliance/csp` | Run Module 6 compliance analysis. |
| `POST /api/planning/search` | Run Module 7 UCS or A* planning. |
| `POST /api/analysis/run` | Run Module 8 integrated analysis. |
| `POST /api/evaluation/run` | Run Module 9 benchmarks. |

Every API request returns an `X-Request-ID` header for correlation. Error responses are JSON and never intentionally include stack traces, MongoDB URIs, upload content, or filesystem paths.

## Tests and production build

```powershell
cd backend
$env:PYTHONPATH='.'
..\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
```

`frontend/dist/`, `node_modules/`, `.venv/`, bytecode, caches, and `.env` files are ignored by Git. The frontend production bundle can be served as static files by the deployment platform of choice; it is not committed to this repository.

## Deployment checklist

1. Set `APP_ENV=production`, an explicit `FRONTEND_ORIGINS` allow-list, and `ENABLE_API_DOCS=false` unless protected docs are required.
2. Set a production `VITE_API_BASE_URL` before building the frontend.
3. Run the backend behind a production ASGI process manager/reverse proxy with TLS termination, request-size controls, and process-level timeouts.
4. Supply `MONGO_URI` only when a deployed feature genuinely uses persistence; otherwise leave it unset.
5. Monitor the structured JSON-line logs using request IDs. Logs contain method, path, status, duration, and error type—not request bodies, PDFs, or credentials.

## Known limitations

- PDF extraction is heuristic and does not perform OCR; scanned/image-heavy documents may return warnings or limited structure.
- Logical verification is bounded to avoid exponential model and clause growth.
- Compliance results cover the supported declarative profile requirements only.
- Improvement plans are hypothetical state-space recommendations. They never edit PDFs, generate prose, or invent citations.
- The current repository does not persist papers or analysis history to MongoDB.
