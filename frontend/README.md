# PaperIntel AI — Frontend

Intelligent Research Paper Analysis and Improvement Assistant.

This repository contains **only the frontend** of PaperIntel AI, built with React + Vite + Tailwind CSS.
The backend (FastAPI + MongoDB) is developed separately and is not part of this project.

## Getting started

```bash
npm install
npm run dev
```

Then open the printed local URL (typically `http://localhost:5173`).

## Build for production

```bash
npm run build
npm run preview   # optional: preview the production build locally
```

## Project structure

```
frontend/
├── src/
│   ├── components/    Reusable UI pieces (Navbar, Footer, ScoreCard, ScoreRing, Icon, UploadDropzone)
│   ├── layouts/        MainLayout.jsx (Navbar + Footer + page outlet)
│   ├── pages/          One file per route (Home, Analyze, Dashboard, ModuleDetail, History, About, NotFound)
│   ├── routes/         AppRoutes.jsx — all route definitions
│   ├── services/       api.js (future backend contract) + mockData.js (frontend-only mock data)
│   ├── styles/         global.css — non-utility global styles
│   ├── utils/          formatScore.js, formatDate.js
│   ├── App.jsx
│   ├── index.css       Tailwind entrypoint
│   └── main.jsx
├── index.html
├── tailwind.config.js
├── postcss.config.js
├── vite.config.js
├── eslint.config.js
└── package.json
```

## Pages implemented

| Route                  | Page            | Notes |
|-------------------------|-----------------|-------|
| `/`                     | Home            | Hero, eight-module feature grid, how-it-works, benefits, CTA |
| `/analyze`               | Analyze Paper   | PDF drag-and-drop upload, guideline selector, module toggles |
| `/dashboard`             | Dashboard       | Overall score ring, per-module chart, module cards, strengths/weaknesses, priority improvements |
| `/dashboard/:module`     | Module Detail   | Reusable detail view for any of the eight modules (issue, evidence, explanation, recommendation) |
| `/history`               | History         | Searchable, filterable, sortable table of past analyses |
| `/about`                 | About           | Project explanation, AI concepts, tech stack |
| `*`                      | Not Found       | 404 page |

## Reusable components

- **Navbar / Footer** — responsive site chrome, with a mobile menu.
- **ScoreRing** — the signature visualization: a radial dial where each of the eight modules gets its own arc segment, sized by weight and colored by status.
- **ScoreCard** — one evaluation module's score, weight, status, and description; reused for all eight modules on the dashboard.
- **UploadDropzone** — drag-and-drop / browse PDF picker (UI only, no parsing).
- **Icon** — small dependency-free inline SVG icon set.

## Mock data → real API

All screens currently read from `src/services/mockData.js`, which mirrors the exact shape the backend is expected to return (`MOCK_REPORT`, `MOCK_MODULE_DETAILS`, `MOCK_HISTORY`, `MODULES`).

`src/services/api.js` defines the future Axios-based contract (`uploadPaper`, `analyzePaper`, `getReport`, `getHistory`, `deleteHistoryEntry`) — each function currently throws a clear "not implemented" error. To connect the real FastAPI backend later:

1. Implement each function body in `api.js` (uncomment the sketched Axios calls, point `VITE_API_BASE_URL` at the backend).
2. In each page, replace the `MOCK_*` import with a call to the matching `api.js` function (e.g. `getReport(analysisId)` instead of `MOCK_REPORT`).
3. Because the mock data already matches the intended API response shape, no component markup should need to change — only the data source.

## Tech stack

- React 18 + Vite
- React Router v6
- Tailwind CSS
- Axios (client scaffold only, no live requests yet)
- Recharts (module score bar chart)
