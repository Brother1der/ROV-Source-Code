import type { JSX } from 'react';
import type { DataPoint, MissionState } from '../../types/mission';

type Props = {
  dataPoints: DataPoint[];
  maxDepth: number;
  missionState: MissionState;
};

const W = 600, H = 220;
const PAD = { top: 16, right: 16, bottom: 36, left: 52 };
const GW = W - PAD.left - PAD.right;
const GH = H - PAD.top - PAD.bottom;
const Y_TICKS = 5;
const X_TICKS = 6;

export default function DepthGraph({ dataPoints, maxDepth, missionState }: Props): JSX.Element {
  const yMax = maxDepth > 0 ? maxDepth * 1.15 : 5;
  const xMax = dataPoints.length > 1 ? dataPoints[dataPoints.length - 1].t : 60;

  const toX = (t: number) => PAD.left + (t / xMax) * GW;
  const toY = (d: number) => PAD.top + (d / yMax) * GH;

  const pathD = dataPoints.length < 2 ? '' :
    dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'}${toX(p.t).toFixed(1)},${toY(p.d).toFixed(1)}`).join(' ');

  const areaD = pathD
    ? `${pathD} L${toX(dataPoints[dataPoints.length - 1].t).toFixed(1)},${toY(0).toFixed(1)} L${toX(0).toFixed(1)},${toY(0).toFixed(1)} Z`
    : '';

  const last = dataPoints[dataPoints.length - 1];

  return (
    <div className="rounded-xl border overflow-hidden bg-[#F7FAFA] border-[#C8E0DF]">
      <div className="px-4 pt-3 pb-1 flex items-center gap-2">
        <i className="fa-solid fa-chart-line text-sm text-[#1B6B68]" />
        <span className="font-bold text-sm tracking-wide uppercase text-[#1B6B68]">
          Depth Profile
        </span>
        {last && (
          <span className="ml-auto text-xs font-mono text-[#2D8B84]">
            {last.d.toFixed(2)} m
          </span>
        )}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 260 }}>
        <defs>
          <linearGradient id="depthGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2D8B84" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#2D8B84" stopOpacity="0.02" />
          </linearGradient>
          <clipPath id="graphClip">
            <rect x={PAD.left} y={PAD.top} width={GW} height={GH} />
          </clipPath>
        </defs>

        {Array.from({ length: Y_TICKS + 1 }, (_, i) => {
          const d = (yMax / Y_TICKS) * i;
          const y = toY(d);
          return (
            <g key={i}>
              <line x1={PAD.left} y1={y} x2={PAD.left + GW} y2={y}
                stroke="#C8E0DF" strokeWidth="1"
                strokeDasharray={i === 0 ? undefined : '4 3'} />
              <text x={PAD.left - 6} y={y + 4} textAnchor="end"
                fontSize="10" fill="#6B9E9B" fontFamily="monospace">
                {d.toFixed(1)}
              </text>
            </g>
          );
        })}

        {Array.from({ length: X_TICKS + 1 }, (_, i) => {
          const t = (xMax / X_TICKS) * i;
          const x = toX(t);
          return (
            <g key={i}>
              <line x1={x} y1={PAD.top} x2={x} y2={PAD.top + GH}
                stroke="#C8E0DF" strokeWidth="1" strokeDasharray="4 3" />
              <text x={x} y={PAD.top + GH + 14} textAnchor="middle"
                fontSize="10" fill="#6B9E9B" fontFamily="monospace">
                {Math.round(t)}s
              </text>
            </g>
          );
        })}

        <rect x={PAD.left} y={PAD.top} width={GW} height={GH}
          fill="none" stroke="#A0C4C2" strokeWidth="1.5" />

        {areaD && <path d={areaD} fill="url(#depthGrad)" clipPath="url(#graphClip)" />}
        {pathD && (
          <path d={pathD} fill="none" stroke="#1B6B68" strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round" clipPath="url(#graphClip)" />
        )}

        {last && missionState === 'running' && (
          <circle cx={toX(last.t)} cy={toY(last.d)} r="4"
            fill="#1B6B68" stroke="#fff" strokeWidth="2">
            <animate attributeName="r" values="4;6;4" dur="1.2s" repeatCount="indefinite" />
          </circle>
        )}
        {last && missionState !== 'running' && (
          <circle cx={toX(last.t)} cy={toY(last.d)} r="4"
            fill="#1B6B68" stroke="#fff" strokeWidth="2" />
        )}

        {dataPoints.length === 0 && (
          <text x={W / 2} y={H / 2} textAnchor="middle" fontSize="12" fill="#A0C4C2">
            No data — start a mission to begin profiling
          </text>
        )}

        <text x={14} y={PAD.top + GH / 2} textAnchor="middle" fontSize="10" fill="#6B9E9B"
          transform={`rotate(-90, 14, ${PAD.top + GH / 2})`}>
          DEPTH (m)
        </text>
      </svg>
    </div>
  );
}
