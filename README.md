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

## Deploy on another machine (Docker — recommended)

The repo includes a **single Docker image** that builds the React app and runs **Gunicorn** on port **5050** (API + static UI). Whisper/LLM calls use a **600s** worker timeout.

1. Install [Docker](https://docs.docker.com/get-docker/) on the target system.
2. Copy the project (or `git clone`) and add a **`.env`** file next to `.env.example` with your API keys (never commit `.env`).
3. From the **project root** (where `Dockerfile` lives):

   ```bash
   docker compose -f docker-compose.prod.yml up --build -d
   ```

4. Open **`http://localhost:8080`** (host port **8080** → container **5050**).

The compose file mounts a volume so **SQLite** data under `backend/instance` survives restarts. To re-seed the question bank after schema changes, run once inside the container:

```bash
docker compose -f docker-compose.prod.yml exec web python seed_db.py
```

**Plain Docker (no Compose):**

```bash
docker build -t interview-coach .
docker run --env-file .env -p 8080:5050 -v coach_data:/app/backend/instance interview-coach
```

**Split hosting (UI on Netlify/Vercel, API on a server):**

1. Build the frontend with your public API URL:

   ```bash
   docker build --build-arg VITE_API_BASE=https://api.yourdomain.com -t interview-api .
   ```

   Or locally: `VITE_API_BASE=https://api.yourdomain.com npm run build` in `frontend/`.

2. Deploy the built `frontend/dist` to the static host.

3. Run the backend image **without** baking the SPA (or set `FRONTEND_DIST` empty) if the API only serves `/api/*`; set **`CORS_ORIGINS`** to your static site origin (e.g. `https://yourapp.netlify.app`).

**Manual production (no Docker):**

```powershell
cd frontend
npm ci
npm run build
cd ..\backend
$env:FRONTEND_DIST = "$(Resolve-Path ..\frontend\dist)"
$env:CORS_ORIGINS = "http://localhost:8080"
.\.venv\Scripts\python.exe seed_db.py
.\.venv\Scripts\gunicorn.exe --bind 0.0.0.0:5050 --workers 1 --timeout 600 wsgi:app
```

Then open `http://localhost:5050`. Use a reverse proxy (nginx, Caddy) for HTTPS in production.

**PostgreSQL:** Start `docker compose up -d` (dev `docker-compose.yml` has Postgres). Set `DATABASE_URL=postgresql://coach:coach@localhost:5432/interview_coach`, run `seed_db.py`, then run the app or rebuild the Docker image.

## Public HTTPS link for an external system

Nobody can give you the final URL until **you** deploy (the hostname is chosen on the platform). Use one of these:

### A) [Render](https://render.com/) (simplest UI)

1. Push this repo to GitHub (e.g. [your INTERVIEW repo](https://github.com/raga952003-cmyk/INTERVIEW)).
2. In Render: **New → Blueprint** → connect the repo → it reads [`render.yaml`](render.yaml).
3. In the service **Environment** tab, add at least: `OPENAI_API_KEY`, `GOOGLE_API_KEY` (and/or `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`). Optionally `SECRET_KEY`, `CORS_ORIGINS` (your Render URL once known).
4. After deploy, Render shows your link, typically **`https://<service-name>.onrender.com`** — use that in the browser on any machine.

**Caveat:** Free web services may **stop after idle** (cold start ~1 min) and can enforce **short HTTP timeouts** (~100s), which may break **very long** record → Whisper → judge flows. For heavy use, prefer Fly.io or a VPS.

### B) [Fly.io](https://fly.io/)

1. Install the [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/), then from the repo root: `fly launch` (use the included [`fly.toml`](fly.toml); change `app` to a **globally unique** name).
2. `fly secrets set OPENAI_API_KEY=... GOOGLE_API_KEY=...` (and any other keys from `.env.example`).
3. `fly deploy` → open **`https://<your-app>.fly.dev`**.

### C) Tunnel (no cloud deploy — link in minutes)

1. Run the app locally: `docker compose -f docker-compose.prod.yml up --build` (or Gunicorn + `FRONTEND_DIST`).
2. Install [ngrok](https://ngrok.com/) (or [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)) and run e.g. `ngrok http 8080`.
3. Use the HTTPS URL ngrok prints (e.g. **`https://abc123.ngrok-free.app`**) on external systems. Stops when your PC/tunnel stops.

---

**Same-origin UI:** The Docker image serves the React build and `/api` on **one** host, so you do **not** need `VITE_API_BASE` for Render/Fly/ngrok as long as you open the app at that HTTPS origin.

## Scraping (optional, offline)

The blueprint described scraping to fill `questions`. This repo ships **curated seeds** in `seed_db.py`. Any scraper should stay a **separate offline job** that respects site terms and then inserts rows into PostgreSQL.

## Gemini SDK note

You may see a `FutureWarning` from `google.generativeai`; Google recommends migrating to `google.genai` over time. The app works with the current package; upgrade the client when you are ready to change the judge integration code.
