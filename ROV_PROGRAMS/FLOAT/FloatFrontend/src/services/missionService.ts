import type { DataPoint, ApiStatus, ApiMissionData } from '../types/mission';

export const DEPTH_PROFILE: DataPoint[] = [
  { t: 0,  d: 0.00 }, { t: 5,  d: 0.40 }, { t: 10, d: 1.10 },
  { t: 18, d: 2.30 }, { t: 26, d: 3.50 }, { t: 32, d: 4.20 },
  { t: 38, d: 4.20 }, { t: 44, d: 4.18 }, { t: 50, d: 3.10 },
  { t: 56, d: 1.80 }, { t: 62, d: 0.50 }, { t: 67, d: 0.05 },
];

export function interpolateDepth(t: number): number {
  if (t <= DEPTH_PROFILE[0].t) return DEPTH_PROFILE[0].d;
  if (t >= DEPTH_PROFILE[DEPTH_PROFILE.length - 1].t) return DEPTH_PROFILE[DEPTH_PROFILE.length - 1].d;
  for (let i = 0; i < DEPTH_PROFILE.length - 1; i++) {
    if (t >= DEPTH_PROFILE[i].t && t < DEPTH_PROFILE[i + 1].t) {
      const ratio = (t - DEPTH_PROFILE[i].t) / (DEPTH_PROFILE[i + 1].t - DEPTH_PROFILE[i].t);
      return DEPTH_PROFILE[i].d + ratio * (DEPTH_PROFILE[i + 1].d - DEPTH_PROFILE[i].d);
    }
  }
  return 0;
}

export function getNow(): string {
  const d = new Date();
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map(n => String(n).padStart(2, '0'))
    .join(':');
}

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://raspberrypi.local:5000';

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
