const BASE = import.meta.env.DEV ? '' : ''

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path)
  if (!res.ok) throw new Error(`HTTP ${res.status} — ${res.statusText}`)
  return res.json() as Promise<T>
}

export default apiFetch
