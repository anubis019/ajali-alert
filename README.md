# Ajali Alert (demo build)

A scoped-down, actually-runnable slice of the Ajali Alert spec: the backend
API (incident reporting, nearest-responder dispatch, escalation, status
timeline, live websocket updates) plus the citizen web app (report an
emergency, track it live).

What's **not** in this build, on purpose: Postgres/PostGIS, Redis, auth/JWT,
the dispatcher/responder/admin consoles, USSD, SMS/push/email providers,
Docker/Nginx. Those all assume infrastructure this demo doesn't set up. The
dispatch and escalation *logic* from the spec is still here, just running
against SQLite with an in-process websocket broadcaster instead of Postgres
+ Redis.

## What's inside

- **Backend** (`backend/`) - FastAPI + SQLite: incident reporting, nearest-
  responder dispatch (haversine, no PostGIS needed), auto-escalation when
  nobody's in range, status timeline, live websocket updates, and a local
  first-aid guidance engine.
- **Frontend** (`frontend/index.html`) - single static file: report an
  emergency, track it live, and see matched first-aid guidance while you
  wait.

## First-aid assistant

This is a **local, offline knowledge base with keyword matching** -
deliberately not a live generative AI call. In an emergency context that's
the safer tradeoff: it works with no connectivity, gives the same answer
every time for the same input, and every line of guidance in
`backend/first_aid_kb.py` can be reviewed and signed off before it ships,
rather than generated fresh under pressure.

- `backend/first_aid_kb.py` - the data. This is "the local data you feed
  it": edit or extend the `TOPICS` list to add more scenarios. Each topic
  has `keywords` (drives matching), `types` (which incident types surface
  it by default), `steps`, and `warnings`.
- `backend/first_aid.py` - the matcher. Scores keyword overlap between the
  incident description (or a free-text follow-up question) and the KB,
  weighted so longer/more specific phrase matches outrank single-word
  overlaps. No ML libraries, no network call.
- On incident creation and every fetch, the API attaches the top matches as
  `first_aid_suggestions`. `POST /api/v1/first-aid/ask` takes a free-text
  question (optionally scoped to an incident) for follow-ups.
- The frontend shows these as an expandable "While you wait" card on the
  tracking view, plus a text box for follow-up questions.

If you want a real LLM in the loop later, `first_aid.py` has a
`rephrase_hook()` seam for it - the intent is to let a model *reword or
expand* the already-matched, vetted steps for tone, never to let it
originate medical content itself.

## Run the backend

Requires Python 3.10+.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

This creates `ajali.db` (SQLite) on first run, seeds 5 incident types and 6
responders scattered around Nairobi, and serves the API at
`http://localhost:8000`. Interactive docs: `http://localhost:8000/api/docs`.

## Run the frontend

No build step - it's one static HTML file.

```bash
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500`. Allow location access when prompted (or just
type a location description - it'll fall back to a default Nairobi CBD
point). Select an emergency type, describe what's happening, submit, and
you'll land on a live tracking view that updates over the websocket as the
incident's status changes.

To see status changes happen, use the interactive API docs
(`/api/docs` → `PATCH /api/v1/incidents/{id}/status`) to walk an incident
through `DISPATCHING → EN_ROUTE → ARRIVED → RESOLVED → CLOSED` and watch the
tracking page update in real time.

## What I couldn't verify here

I don't have network/package-install access in this sandbox, so I
syntax-checked every backend file (`py_compile`) but couldn't actually
`pip install` and run the server end-to-end. The logic is straightforward
FastAPI/SQLAlchemy with no exotic dependencies, so it should run as-is, but
flag it if you hit an import or startup error and I'll fix it.

## Layout

```
ajali-alert/
├── backend/
│   ├── main.py          # FastAPI app: routes, dispatch, escalation, websocket
│   ├── models.py        # SQLAlchemy models (SQLite)
│   ├── schemas.py        # Pydantic request/response models
│   ├── seed.py           # Seeds incident types + demo responders
│   ├── first_aid_kb.py   # Local first-aid knowledge base (edit this to feed more data)
│   ├── first_aid.py      # Keyword-matching engine over the KB
│   └── requirements.txt
├── frontend/
│   └── index.html        # Citizen web app (report + track + first aid), no build step
└── README.md
```

## Extending this

Natural next slices, in order of what'd build on this cleanly:
1. **Dispatcher console** - a second static page hitting the same API
   (`GET /api/v1/incidents`, `PATCH .../status`) plus a map.
2. **Auth** - add JWT login so incidents/responders aren't fully open.
3. **Swap SQLite → Postgres+PostGIS** - only `models.py`'s engine URL and
   the haversine helper in `main.py` would need to change; the dispatch
   logic already isolates "find nearest responder" into one function.
