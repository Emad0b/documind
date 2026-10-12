export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const r = await fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
  });
  if (!r.ok) {
    let message = "Server unavailable. Check the FastAPI backend.";
    try {
      const e = await r.json();
      message =
        typeof e.detail === "string" ? e.detail : JSON.stringify(e.detail);
    } catch {}
    throw new Error(message);
  }
  return r.json() as Promise<T>;
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
