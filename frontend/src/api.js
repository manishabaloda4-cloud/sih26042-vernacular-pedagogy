const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function get(path, params = {}) {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null));
  const r = await fetch(`${BASE}${path}?${new URLSearchParams(clean)}`);
  if (!r.ok) {
    let msg = `Server error ${r.status}`;
    try { msg = (await r.json()).detail || msg; } catch { /* ignore */ }
    throw new Error(msg);
  }
  return r.json();
}

export const health = () => get("/health");
export const translate = (q) => get("/api/v1/translate", { q });
export const phrases = (p) => get("/api/v1/phrases", p);
export const worksheet = (p) => get("/api/v1/worksheet", p);
export const ttsUrl = (text) => `${BASE}/api/v1/tts?${new URLSearchParams({ text, lang: "pa" })}`;

// Plays Punjabi audio; resolves with milliseconds until sound started.
export function speak(text) {
  return new Promise((resolve, reject) => {
    const a = new Audio(ttsUrl(text));
    const t0 = performance.now();
    a.addEventListener("playing", () => resolve(performance.now() - t0), { once: true });
    a.addEventListener("error", () => reject(new Error("Audio could not be loaded. Is the server online?")), { once: true });
    a.play().catch(reject);
  });
}
