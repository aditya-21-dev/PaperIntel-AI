# PaperIntel AI frontend

React, Vite, Tailwind CSS, and Axios client for the PaperIntel AI FastAPI backend. The current screens call the live API for PDF processing, knowledge, reasoning, logic, compliance, planning, integrated analysis, and system evaluation.

See the [project README](../README.md) for the complete architecture, environment variables, backend setup, tests, security notes, and deployment checklist.

## Getting started

```bash
npm install
npm run dev
```

Copy `.env.example` to `.env` when a non-default backend URL is needed. Then open the printed local URL, normally `http://localhost:5173`.

## Configuration

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

`VITE_API_BASE_URL` must match an origin in the backend's `FRONTEND_ORIGINS` configuration. API failures are shown in the affected page and loading actions are disabled while a request is in progress.

## Production build

```bash
npm run build
npm run preview
```

The generated `dist/` directory is intentionally ignored by Git.
