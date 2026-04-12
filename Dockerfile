# Single image: Vite build + Gunicorn (API + static UI on one port).
# Build: docker build -t interview-coach .
# Run:   docker run --env-file .env -p 8080:5050 interview-coach

FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Same-origin API: leave empty. For split hosting (UI on CDN), pass:
#   docker build --build-arg VITE_API_BASE=https://api.yourdomain.com .
ARG VITE_API_BASE=
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# faster-whisper / PyAV decode WebM and video uploads reliably
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /build/dist /app/frontend/dist

ENV FRONTEND_DIST=/app/frontend/dist
WORKDIR /app/backend
EXPOSE 5050
ENV PORT=5050

# PORT is overridden by Render, Railway, Fly.io, etc. Local Docker defaults to 5050.
CMD ["sh", "-c", "python seed_db.py && exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --timeout 600 --graceful-timeout 60 wsgi:app"]
