import type { ApiStatus, ApiMissionData } from '../types/mission';

export function getNow(): string {
  const d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0'))
    .join(':');
}

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

export async function apiStartMission(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/start`, { method: 'POST' });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { error?: string };
    throw new Error(body.error ?? `Start failed: ${res.status}`);
  }
}

export async function apiGetStatus(): Promise<ApiStatus> {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error(`Status check failed: ${res.status}`);
  return res.json() as Promise<ApiStatus>;
}

export async function apiGetData(): Promise<ApiMissionData> {
  const res = await fetch(`${API_BASE}/api/data`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { error?: string };
    throw new Error(body.error ?? `Data fetch failed: ${res.status}`);
  }
  return res.json() as Promise<ApiMissionData>;
}
