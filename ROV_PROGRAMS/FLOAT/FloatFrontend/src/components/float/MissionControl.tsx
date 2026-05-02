import type { JSX } from 'react';
import Button from '@mui/material/Button';
import type { MissionState, MissionStats } from '../../types/mission';

type Props = {
  missionState: MissionState;
  onStart: () => void;
  onReset: () => void;
  stats: MissionStats;
};

type StatItem = {
  icon: string;
  label: string;
  value: string;
};

export default function MissionControl({ missionState, onStart, onReset, stats }: Props): JSX.Element {
  const isActive = ['connecting', 'running', 'receiving'].includes(missionState);
  const isDone = missionState === 'complete';
  const canStart = missionState === 'idle' || missionState === 'error';

  const buttonLabel = isActive ? (
    <>
      <i className="fa-solid fa-spinner fa-spin text-base mr-3" />
      {missionState === 'connecting' ? 'Connecting…' : missionState === 'running' ? 'Running…' : 'Receiving…'}
    </>
  ) : isDone ? (
    <><i className="fa-solid fa-rotate-left text-base mr-3" />Reset</>
  ) : (
    <><i className="fa-solid fa-play text-base mr-3" />Start Mission</>
  );

  const statItems: StatItem[] = [
    {
      icon: 'fa-arrow-down',
      label: 'Max Depth',
      value: stats.maxDepth != null ? `${stats.maxDepth.toFixed(2)} m` : '—',
    },
    {
      icon: 'fa-clock',
      label: 'Duration',
      value: stats.duration != null ? `${stats.duration} s` : '—',
    },
    {
      icon: 'fa-chart-simple',
      label: 'Data Pts',
      value: stats.points != null ? String(stats.points) : '—',
    },
  ];

  return (
    <div className="rounded-xl border overflow-hidden border-[#C8E0DF] bg-[#F7FAFA]">
      <div className="px-4 py-2.5 border-b flex items-center gap-2 bg-[#1B6B68] border-[#2D8B84]">
        <i className="fa-solid fa-satellite-dish text-sm text-[#7EC8C4]" />
        <span className="font-medium text-sm tracking-wide uppercase text-[#E0F4F3]"
          style={{ letterSpacing: '0.04em' }}>
          Mission Control
        </span>
      </div>

      <div className="p-4 flex flex-col gap-4">
        <Button
          variant="contained"
          fullWidth
          disabled={isActive}
          onClick={canStart ? onStart : isDone ? onReset : undefined}
          sx={{
            py: 1.5,
            fontSize: '1.1rem',
            fontWeight: 600,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            backgroundColor: isActive ? '#A0C4C2' : isDone ? '#0D6B60' : '#1B6B68',
            boxShadow: isActive ? 'none' : '0 4px 18px rgba(27,107,104,0.35)',
            '&:hover': {
              backgroundColor: isActive ? '#A0C4C2' : isDone ? '#0A5A50' : '#155755',
            },
            '&.Mui-disabled': {
              backgroundColor: '#A0C4C2',
              color: '#fff',
            },
          }}
        >
          {buttonLabel}
        </Button>

        <div className="grid grid-cols-3 gap-3">
          {statItems.map(({ icon, label, value }) => (
            <div key={label}
              className="rounded-lg p-3 flex flex-col items-center gap-1 border bg-[#EBF5F4] border-[#C8E0DF]">
              <i className={`fa-solid ${icon} text-xs text-[#2D8B84]`} />
              <span className="text-lg font-semibold leading-none text-[#1B6B68]">{value}</span>
              <span className="text-xs uppercase tracking-wide text-[#6B9E9B]">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
