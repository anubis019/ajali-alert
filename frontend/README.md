# AJALI ALERT SYSTEM — Frontend

> **Ajali** (Swahili: *emergency / accident*) — a real-time emergency command center dashboard for Kenya.

## Overview

A public-facing emergency dashboard with an admin-only JARVIS AI layer. Built as a static single-page app for Vercel deployment, connecting to a FastAPI + SQLite + JWT backend on Render.

### Public (no login required)
- Live alert feed with severity indicators
- Key metrics (total alerts, critical count, active incidents, golden-hour window)
- Severity & county distribution charts
- Kenya response team status cards
- County & severity filters

### Admin-only (JARVIS AI features)
- **Triage** — AI-prioritized alert queue
- **Dispatch** — Nearest team suggestions with ETAs
- **Brief** — Situational intelligence summaries per alert
- **Predict** — Risk forecasting by county
- **USSD Chat** — 12-turn, 160-char USSD-style interface (*1233#)

## Quick Deploy (Vercel)

```bash
# 1. Clone or upload this folder to a GitHub repo
# 2. Import into Vercel
# 3. Set environment variable (optional):
#    VITE_API_BASE = https://ajali-api.onrender.com
# 4. Deploy — done!
```

Or deploy directly:
```bash
cd ajali-frontend
npx vercel --prod
```

## Backend

The frontend expects a FastAPI backend at the configured API base URL (default: `https://ajali-api.onrender.com`).

### API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | OAuth2 login (form-encoded) |
| POST | `/api/v1/jarvis/triage` | Alert triage |
| POST | `/api/v1/jarvis/dispatch-suggest` | Dispatch suggestions |
| GET  | `/api/v1/jarvis/brief/{id}` | Alert intelligence brief |
| GET  | `/api/v1/jarvis/predict` | Risk prediction |
| POST | `/api/v1/jarvis/chat` | USSD chat session |

### Default Credentials
| Username | Password | Role |
|----------|----------|------|
| admin | admin1234 | Admin |
| sarah.chen | responder1 | Responder |
| james.okafor | responder2 | Responder |

## Tech Stack

- **Pure HTML/CSS/JS** — no build step, no framework
- **Chart.js** — dashboard visualizations
- **DM Mono + Instrument Sans** — typography
- **Dark command-center aesthetic** — `#0a0b0d` base, amber/red/teal accents, scanline overlay

## Customization

- Change API base URL: Edit `js/config.js` or set via the login modal's "API Base" field
- Kenya counties: Edit `CONFIG.COUNTIES` in `js/config.js`
- Response teams: Edit `AlertData.getTeams()` in `js/data.js`
- Color tokens: Edit `css/variables.css`

## Folder Structure

```
ajali-frontend/
├── index.html          # Main SPA
├── vercel.json         # Vercel routing config
├── css/
│   ├── variables.css   # Design tokens
│   ├── base.css        # Reset, body, ambient bg, scanline
│   ├── login.css       # Admin login modal
│   ├── header.css      # Site header
│   ├── filters.css     # County/severity filters
│   ├── metrics.css     # Metric cards
│   ├── jarvis.css       # JARVIS panel + all 5 tabs
│   ├── charts.css      # Chart cards
│   ├── feed.css        # Alert feed list
│   ├── modal.css       # Alert detail modal
│   ├── teams.css       # Response team cards
│   ├── toast.css       # Toast notifications
│   ├── footer.css      # Footer
│   └── responsive.css  # Media queries
├── js/
│   ├── config.js       # App configuration
│   ├── api.js          # API client
│   ├── auth.js         # Auth manager
│   ├── toast.js        # Toast notification system
│   ├── modal.js        # Modal manager
│   ├── jarvis.js       # JARVIS panel controller + tabs
│   ├── triage.js       # Triage module
│   ├── dispatch.js     # Dispatch module
│   ├── brief.js        # Brief module
│   ├── predict.js      # Predict module
│   ├── chat.js         # USSD chat module
│   ├── data.js         # Mock data generator
│   ├── charts.js       # Chart renderer
│   ├── filters.js      # Filter controls
│   ├── feed.js         # Alert feed renderer
│   ├── teams.js        # Team cards renderer
│   ├── simulation.js   # Live simulation engine
│   └── app.js          # App init + auth binding
└── assets/             # Static assets (favicons, etc.)
```

## License

MIT — Built with urgency for Kenya's emergency response.
