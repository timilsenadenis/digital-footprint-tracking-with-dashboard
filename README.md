# 🔍 Digital Footprint Tracker

> An undergraduate database project built with **PostgreSQL**, **Flask**, and a **Chrome Extension** that tracks your web activity and visualizes it on a real-time dashboard.

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![Python](https://img.shields.io/badge/Python-3.11-yellow?logo=python)
![Chrome](https://img.shields.io/badge/Chrome-Extension-green?logo=googlechrome)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)

---

## 📌 About the Project

Digital Footprint Tracker is a full-stack undergraduate project that demonstrates advanced PostgreSQL features by tracking and analyzing a user's digital activity across the web.

A **Chrome Extension** silently collects browsing data and sends it to a **Flask REST API**, which stores everything in a **PostgreSQL** database. A **Plotly-powered dashboard** then visualizes the data with interactive charts.

---

## 🎯 Features

- 🌐 **Website visit tracking** — URL, domain, title, duration
- 🔎 **Search history** — query, engine, keyword frequency
- 💬 **Social media activity** — likes, posts, shares, scroll depth
- ⏱️ **App usage time** — session tracking per application
- 📊 **Interactive dashboard** — heatmaps, pie charts, bar charts, trend lines
- 🔐 **JWT authentication** — secure login for extension and dashboard
- 🛡️ **Row-Level Security** — users only see their own data

---

## 🗄️ PostgreSQL Features Showcased

| Feature | Usage |
|---|---|
| **Table Partitioning** | `visits` table partitioned by month for performance |
| **Triggers** | Auto domain extraction, auto-categorization, audit logging |
| **Materialized Views** | `daily_summary`, `top_domains_weekly` for fast queries |
| **Window Functions** | `RANK()`, `LAG()`, running totals, session detection |
| **JSONB Columns** | Raw payload storage for flexible metadata |
| **Row-Level Security** | Users can only access their own rows |
| **Generated Columns** | `duration_sec` auto-computed from timestamps |
| **pg_trgm Extension** | Fuzzy search on URLs and search queries |
| **CTEs** | Complex analytics queries |

---

## 🏗️ System Architecture

```
┌─────────────────────┐
│   Chrome Extension  │  ← Tracks visits, searches, social events
│   (Manifest V3)     │
└────────┬────────────┘
         │ HTTP POST (JSON)
         ▼
┌─────────────────────┐
│   Flask REST API    │  ← Auth, validation, rate limiting
│   (Python 3.11)     │
└────────┬────────────┘
         │ psycopg2
         ▼
┌─────────────────────┐
│    PostgreSQL 16    │  ← Triggers, views, RLS, partitioning
│    (Database)       │
└────────┬────────────┘
         │ SQL queries
         ▼
┌─────────────────────┐
│  Flask + Plotly.js  │  ← Interactive charts and dashboard
│  (Dashboard)        │
└─────────────────────┘
```

---

## 📁 Project Structure

```
digital-footprint-tracker/
├── backend/
│   ├── app.py               ← Flask REST API (auth + tracking + analytics)
│   ├── models.py            ← Python DB model classes
│   ├── schema.sql           ← PostgreSQL tables, indexes, views
│   ├── triggers.sql         ← All 6 PostgreSQL triggers
│   ├── requirements.txt     ← Python dependencies
│   └── Dockerfile           ← Multi-stage Docker build
├── dashboard/
│   ├── charts.py            ← Server-side Plotly chart generators
│   ├── static/
│   │   ├── css/style.css    ← Dashboard stylesheet
│   │   └── js/charts.js     ← Client-side Plotly functions
│   └── templates/
│       └── dashboard.html   ← Main dashboard UI
├── extension/
│   ├── manifest.json        ← Chrome Manifest V3
│   ├── background.js        ← Visit, search, app tracking
│   ├── content_social.js    ← Social media action detection
│   ├── popup.html           ← Extension popup UI
│   ├── popup.js             ← Popup logic
│   └── icons/               ← Extension icons
├── docker-compose.yml       ← PostgreSQL + Flask services
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Git](https://git-scm.com/downloads)
- Google Chrome browser

### 1. Clone the repository
```bash
git clone https://github.com/timilsenadenis/digital-footprint-tracking-with-dashboard.git
cd digital-footprint-tracking-with-dashboard
```

### 2. Start with Docker
```bash
docker compose up --build
```

### 3. Load database triggers
```bash
docker exec -i digital-footprint-tracker-db-1 \
  psql -U footprint -d footprint_db \
  < backend/triggers.sql
```

### 4. Open the dashboard
```
http://localhost:5000
```

### 5. Install Chrome Extension
```
1. Open Chrome → chrome://extensions
2. Enable Developer mode (top right)
3. Click "Load unpacked"
4. Select the extension/ folder
```

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Create new account |
| POST | `/api/login` | Login and get JWT token |

### Tracking (called by Chrome Extension)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/track/visit` | Log a URL visit |
| POST | `/api/track/search` | Log a search query |
| POST | `/api/track/social` | Log a social media event |
| POST | `/api/track/app` | Log app usage session |

### Analytics (called by Dashboard)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/summary` | Daily summary stats |
| GET | `/api/analytics/top-domains` | Most visited domains |
| GET | `/api/analytics/categories` | Category breakdown |
| GET | `/api/analytics/heatmap` | Hour-of-day activity map |
| GET | `/api/analytics/searches` | Search keyword frequency |
| GET | `/api/analytics/social` | Social platform stats |

---

## 📊 Dashboard Pages

| Page | Charts |
|------|--------|
| **Overview** | Daily bar + line chart, category pie, top sites bar |
| **Websites** | Top domains table with category badges |
| **Searches** | Keyword frequency, search engine usage |
| **Social Media** | Time per platform, actions breakdown |
| **Activity Map** | Day × Hour heatmap |

---

## 🗃️ Database Schema

```sql
users              → stores registered users
visits             → URL visits (partitioned by month)
searches           → search queries and engines
social_events      → social media actions
app_usage          → application usage sessions
categories         → website categories lookup
domain_category_map → domain to category mapping
audit_log          → trigger-populated change history
```

### Triggers
```
trg_before_visit_insert    → auto-extracts domain from URL
trg_after_domain_set       → auto-categorizes visit by domain
trg_social_audit           → logs all social event changes
trg_visits_last_active     → updates user.last_active
trg_searches_last_active   → updates user.last_active
trg_visits_deduplicate     → prevents duplicate visits within 3s
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Browser Extension | JavaScript (Manifest V3) |
| Backend API | Python 3.11 + Flask 3.0 |
| Database | PostgreSQL 16 |
| ORM / DB Driver | psycopg2 |
| Authentication | JWT (PyJWT) |
| Visualization | Plotly.js |
| Containerization | Docker + Docker Compose |

---

## ⚙️ Environment Variables

Create `backend/.env`:
```env
DATABASE_URL=postgresql://footprint:footprint@db:5432/footprint_db
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=1
```

---

## 👨‍💻 Author

**Denis Timilsena**
- GitHub: [@timilsenadenis](https://github.com/timilsenadenis)

---

## 📄 License

This project is built for undergraduate academic purposes.