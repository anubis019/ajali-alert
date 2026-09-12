# 🚨 Ajali Alert System

**Kenya Emergency Response Platform** — Real-time dispatch and response for Accidents, Fire, Medical & Security emergencies.

> *Ajali* means *emergency/accident* in Swahili.

---

## 🎯 What It Does

Ajali connects citizens reporting emergencies to the right responders — fast.

| Emergency Type | Examples | Primary Responders |
|---|---|---|
| 🚗 **Accident** | Road collisions, vehicle entrapment, pedestrian incidents | Police + Ambulance |
| 🔥 **Fire** | Structural fires, vehicle fires, chemical spills | Fire Brigade + Ambulance |
| 🏥 **Medical** | Cardiac arrest, maternity emergencies, drowning, trauma | Ambulance |
| 🛡️ **Security** | Armed robbery, home invasion, civil unrest, assaults | Police |

### How Citizens Report
- **USSD** — Dial `*1233#` on any feature phone (primary channel)
- **Mobile App** — Ajali Alert app (smartphones)
- **SMS** — Text alert to shortcode
- **Voice Call** — Call the emergency hotline
- **Web** — Online form at ajali.systems

### How Responders React
- Dispatchers receive alerts in real-time (WebSocket dashboard)
- Auto-notification routes to correct responder type by emergency category
- Escalation enforces **Golden Hour** response targets (2–5 min for critical)
- Full audit trail: dispatching → en_route → on_scene → resolved

---

## 🏗️ Architecture

```
Citizen (USSD/App/SMS/Call)
        │
        ▼
   ┌────────────┐
   │  Ajali API  │  ← FastAPI backend
   │  /api/v1/   │
   └────┬───┬───┬┘
        │   │   │
   ┌────▼┐ │ ┌▼────┐
   │Police│ │ │Fire │  ← Responder types
   └──────┘ │ └─────┘
       ┌────▼────┐
       │Ambulance│
       └─────────┘
```

### Tech Stack
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite/PostgreSQL
- **Auth**: JWT (bcrypt hashing)
- **Real-time**: WebSocket broadcast
- **Notifications**: SMS (Africa's Talking), USSD push, email, Slack, webhooks
- **Escalation**: Category-aware + Golden Hour targets

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env — set JWT_SECRET and SMS provider keys
```

### 3. Run the Server
```bash
uvicorn app.main:app --reload --port 8000
```

The server will:
- Create database tables
- Seed sample data (users, teams, policies, emergency alerts)
- Start the escalation background task

### 4. Access the API
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/v1/health

### 5. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin1234"
```

---

## 📚 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/auth/login` | POST | Login, get JWT token |
| `/api/v1/users/me` | GET | Current user profile |
| `/api/v1/users/` | GET | List users (admin) |
| `/api/v1/alerts/` | GET | List alerts (filterable) |
| `/api/v1/alerts/` | POST | Create emergency alert |
| `/api/v1/alerts/{id}` | GET | Get alert details |
| `/api/v1/alerts/{id}` | PATCH | Update alert |
| `/api/v1/alerts/{id}/acknowledge` | POST | Acknowledge alert |
| `/api/v1/alerts/{id}/resolve` | POST | Resolve alert |
| `/api/v1/alerts/{id}/dispatch` | POST | Quick-dispatch responders |
| `/api/v1/alerts/{id}/events` | GET | Alert event trail |
| `/api/v1/dashboard/stats` | GET | Dashboard statistics |
| `/api/v1/teams/` | GET | List emergency teams |
| `/api/v1/policies/` | GET | List escalation policies |
| `/api/v1/ws` | WS | Real-time WebSocket feed |

### Alert Filters
- `category` — accident, fire, medical, security
- `sub_type` — road_collision, structural_fire, cardiac, robbery, etc.
- `severity` — critical, high, medium, low
- `status` — active, acknowledged, dispatching, en_route, on_scene, escalated, resolved
- `region` — nairobi, mombasa, kisumu, nakuru, eldoret, garissa, meru, kakamega, machakos
- `county` — Filter by Kenya county name
- `responder_type` — police, ambulance, fire_brigade, community_responder

---

## 🗺️ Kenya Counties

The system supports 10 major Kenya counties (expandable to all 47):

Nairobi, Mombasa, Kisumu, Nakuru, Eldoret, Garissa, Meru, Kakamega, Machakos

---

## ⚡ Golden Hour Escalation

Critical emergencies escalate automatically if not responded to within:

| Emergency Type | Critical Escalation Delay |
|---|---|
| 🔥 Fire | 2 minutes |
| 🏥 Medical | 3 minutes |
| 🚗 Accident | 3 minutes |
| 🛡️ Security | 3 minutes |

Escalation repeats every 2–3 minutes until a responder acknowledges.

---

## 📱 USSD Flow (*1233#)

```
1. Dial *1233#
2. Select emergency type:
   1. Accident (gari kugongana)
   2. Fire (moto)
   3. Medical (ugonjwa)
   4. Security (usalama)
3. Confirm location (GPS auto-detected or enter area)
4. Report submitted → responders dispatched
5. Receive SMS confirmation with ETA
```

---

## 👥 Default Users

| Username | Password | Role | Team |
|---|---|---|---|
| admin | admin1234 | Admin | Dispatch HQ |
| sarah.chen | responder1 | Dispatcher | Nairobi Dispatch |
| james.okafor | responder2 | Responder | Nairobi Ambulance |
| officer.wambua | police1 | Responder | Nairobi Police |
| firefighter.akello | fire1 | Responder | Nairobi Fire Brigade |
| boda.kamau | community1 | Responder | Community Responders |
| viewer | viewer1234 | Viewer | — |

---

## 🔧 Deployment

### Render (Recommended)
1. Push to GitHub
2. Connect repo in Render dashboard
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`

### Docker
```bash
docker build -t ajali-backend .
docker run -p 8000:8000 --env-file .env ajali-backend
```

---

## 📄 License

MIT
