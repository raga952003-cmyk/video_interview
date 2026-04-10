/**
 * Production: set VITE_API_BASE to your API origin (e.g. https://api.example.com).
 * Leave empty when the UI is served from the same host as /api (Docker single service).
 */
export function apiUrl(path) {
  const base = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${base}${p}`;
}
