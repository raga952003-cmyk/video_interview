# AI Interview Coach

Web app: enter a **target role** and upload a **resume** (PDF/DOCX/TXT); Gemini summarizes the resume and generates one tailored question. Answer by voice for Whisper transcription plus Gemini-graded feedback. A **quick mode** still pulls random questions from the seeded bank.

## Stack

- **Frontend:** React (Vite), dev proxy to Flask
- **Backend:** Flask, SQLAlchemy, Flask-Limiter, OpenAI Whisper, Google Gemini
- **Database:** SQLite by default, or PostgreSQL (see `docker-compose.yml`)

## Prerequisites

- Python 3.11+
- Node 18+
- [OpenAI API key](https://platform.openai.com/) (Whisper)
- **LLM (at least one):** [Google AI Studio](https://aistudio.google.com/) (`GOOGLE_API_KEY`), [Groq](https://console.groq.com/) (`GROQ_API_KEY`), and/or [Hugging Face](https://huggingface.co/settings/tokens) (`HUGGINGFACE_API_KEY`, optional `HUGGINGFACE_MODEL`, `HUGGINGFACE_BASE_URL`). Order of use: **Gemini → Groq → Hugging Face** until one succeeds.

## Setup

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy ..\.env.example ..\.env
# Edit ..\.env: set OPENAI_API_KEY and GOOGLE_API_KEY
.\.venv\Scripts\python seed_db.py
.\.venv\Scripts\python run.py
```

API runs at **`http://127.0.0.1:5050`** by default (`PORT` in `.env`). Health: `GET /api/health`.

**Windows:** Port **5000** is often used by system services (e.g. AirPlay). If something else already listens on `5050`, set `PORT` to another free port and set the same URL in `frontend/vite.config.js` under `server.proxy["/api"].target`.

### 2. PostgreSQL (optional)

```powershell
docker compose up -d
```

Set in `.env`:

`DATABASE_URL=postgresql://coach:coach@localhost:5432/interview_coach`

Then run `seed_db.py` again.

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to the Flask app (default **`http://127.0.0.1:5050`**).

### Verify the API

With the backend running:

```powershell
cd backend
.\.venv\Scripts\python.exe smoke_http.py http://127.0.0.1:5050
```

All lines should show `OK`. If `/api/health` JSON lacks `database` / `openai_configured`, another program is still bound to that port—pick a free `PORT` and update `vite.config.js` proxy `target` to match.

### Resume-driven questions

- **`POST /api/prepare-from-resume`** — `multipart/form-data`: field **`role`** (free text), file **`resume`** (`.pdf`, `.docx`, or `.txt`). Uses Gemini to produce a short **`resume_summary`**, one **`question_text`**, and a server-stored ideal answer. Response includes **`question_id`** (use this with `analyze-answer` like bank questions).
- **`POST /api/prepare-from-web`** — JSON or form: **`role`**, **`source_url`** (public `http`/`https` only; SSRF-hardened). Fetches the page, extracts text with **BeautifulSoup**, then **Gemini** returns **`resume_summary`** (page insight), **`question_text`**, and a stored ideal answer. Response includes **`source`:** `"web"` and **`source_url`** (final URL after redirects).
- **`POST /api/analyze-answer`** — unchanged; resolves **`question_id`** against the bank, a resume session, or a web session row.

**502 / proxy timeouts:** The Vite dev server proxies `/api` with a **10-minute** timeout so Whisper + Gemini can finish. Production reverse proxies need similarly high read timeouts.

## Environment variables

See `.env.example`. Never commit real API keys.

- `GEMINI_MODEL` — default `gemini-1.5-flash` (override if your account uses another id).
- `CORS_ORIGINS` — comma-separated origins for production SPA hosting.
- `MAX_UPLOAD_MB` — max audio upload size (default 25).

## Production notes

- Run Flask with Gunicorn and timeouts that cover long analyses (e.g. 120s).
- Set `CORS_ORIGINS` to your Netlify/Vercel URL.
- Build the SPA (`npm run build`) and serve `frontend/dist` from a CDN or static host; point API calls to your backend URL (update `fetch` base URL or use a reverse proxy).

## Scraping (optional, offline)

The blueprint described scraping to fill `questions`. This repo ships **curated seeds** in `seed_db.py`. Any scraper should stay a **separate offline job** that respects site terms and then inserts rows into PostgreSQL.

## Gemini SDK note

You may see a `FutureWarning` from `google.generativeai`; Google recommends migrating to `google.genai` over time. The app works with the current package; upgrade the client when you are ready to change the judge integration code.
