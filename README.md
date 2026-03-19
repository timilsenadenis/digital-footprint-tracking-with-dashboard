# Digital Footprint Tracker

Track your web activity — URL visits, searches, social media actions, and app usage — with a Chrome extension that feeds data into PostgreSQL via Flask, visualized with Plotly.

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Browser Extension | JavaScript (Manifest V3) |
| Backend API | Python Flask + psycopg2 |
| Database | PostgreSQL 16 |
| Dashboard | Flask templates + Plotly.js |
| Deployment | Docker Compose |

## PostgreSQL Features Showcased
- **Partitioning** — `visits` table partitioned by month
- **Triggers** — auto domain extraction + auto-categorization on insert
- **Materialized Views** — `daily_summary`, `top_domains_weekly`
- **Window Functions** — `RANK()`, `LAG()`, running totals
- **JSONB** — raw payload storage for flexible metadata
- **Row-Level Security** — users see only their own data
- **pg_trgm** — fuzzy search on URLs and queries
- **Generated Columns** — `duration_sec` auto-computed from timestamps

## Quick Start

### 1. Run with Docker
```bash
docker-compose up --build
```
Dashboard → http://localhost:5000

### 2. Run locally (without Docker)
```bash
# Start PostgreSQL and create DB
psql -U postgres -c "CREATE DATABASE footprint_db;"
psql -U postgres -d footprint_db -f backend/schema.sql

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run Flask
DATABASE_URL=postgresql://postgres@localhost/footprint_db python app.py
```

### 3. Install Chrome Extension
1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked** → select the `extension/` folder
4. Click the extension icon → sign in with your account

## Project Structure
```
digital-footprint-tracker/
├── extension/
│   ├── manifest.json        ← Chrome Manifest V3
│   ├── background.js        ← Visit/search/app tracking
│   ├── content_social.js    ← Social media action detection
│   └── popup.html           ← Extension popup UI
├── backend/
│   ├── app.py               ← Flask REST API
│   ├── schema.sql           ← Full PostgreSQL schema
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/
│   └── templates/
│       └── dashboard.html   ← Plotly.js dashboard
├── docker-compose.yml
└── README.md
```

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Create account |
| POST | `/api/login` | Get JWT token |
| POST | `/api/track/visit` | Log a URL visit |
| POST | `/api/track/search` | Log a search query |
| POST | `/api/track/social` | Log a social event |
| POST | `/api/track/app` | Log app usage |
| GET | `/api/analytics/summary` | Daily summary stats |
| GET | `/api/analytics/top-domains` | Top visited domains |
| GET | `/api/analytics/categories` | Category breakdown |
| GET | `/api/analytics/heatmap` | Hour-of-day heatmap |
| GET | `/api/analytics/searches` | Search keyword frequency |
| GET | `/api/analytics/social` | Social platform stats |

## Dashboard Pages
- **Overview** — total visits, time online, daily bar chart, category pie
- **Websites** — top domains table + horizontal bar chart
- **Searches** — keyword frequency, engine usage
- **Social media** — time per platform, action breakdown
- **Activity map** — day × hour heatmap
