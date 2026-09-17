// Backend endpoints. NEXT_PUBLIC_* values are inlined at build time.
const trim = (url: string) => url.replace(/\/+$/, "");

export const API_URL = trim(process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000");
export const WS_URL = trim(process.env.NEXT_PUBLIC_WS_URL ?? API_URL.replace(/^http/, "ws"));
