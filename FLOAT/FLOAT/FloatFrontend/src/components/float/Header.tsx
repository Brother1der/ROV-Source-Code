import type { JSX } from 'react';
import Chip from '@mui/material/Chip';
import type { MissionState } from '../../types/mission';
import logoSrc from '../../assets/Blue and Black Illustrated Sporting Goods Business Logo - 1.png';

type Props = {
  missionState: MissionState;
};

const STATE_LABEL: Record<MissionState, string> = {
  idle:       'IDLE',
  connecting: 'CONNECTING…',
  running:    'RUNNING',
  receiving:  'RECEIVING DATA…',
  complete:   'COMPLETE',
  error:      'ERROR',
};

const CHIP_COLORS: Record<MissionState, { bg: string; color: string }> = {
  idle:       { bg: '#FEE2E2', color: '#B91C1C' },
  connecting: { bg: '#FEF3C7', color: '#92400E' },
  running:    { bg: '#D1FAE5', color: '#065F46' },
  receiving:  { bg: '#D1FAE5', color: '#065F46' },
  complete:   { bg: '#D1FAE5', color: '#065F46' },
  error:      { bg: '#FEE2E2', color: '#B91C1C' },
};

const DOT_COLOR: Record<MissionState, string> = {
  idle:       'bg-red-500',
  connecting: 'bg-amber-500 animate-pulse',
  running:    'bg-emerald-500 animate-pulse',
  receiving:  'bg-emerald-400 animate-pulse',
  complete:   'bg-emerald-500',
  error:      'bg-red-500',
};

export default function Header({ missionState }: Props): JSX.Element {
  const chip = CHIP_COLORS[missionState];

  return (
    <header className="w-full px-4 py-2.5 flex items-center gap-3 shadow-lg bg-[#1B6B68]">
      <img
        src={logoSrc}
        alt="Lakeview ROV Sub-Aquatics"
        className="flex-shrink-0 h-12 w-12 object-contain"
      />
      <div className="flex-1 min-w-0">
        <div className="font-medium text-white leading-tight text-base">
          Lakeview Sub-Aquatics
        </div>
        <div className="text-xs text-[#7EC8C4]">
          Float Control Interface
        </div>
      </div>
      <Chip
        size="small"
        label={
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full inline-block ${DOT_COLOR[missionState]}`} />
            {STATE_LABEL[missionState]}
          </span>
        }
        sx={{
          backgroundColor: chip.bg,
          color: chip.color,
          fontWeight: 600,
          fontSize: '0.7rem',
          letterSpacing: '0.03em',
          height: 28,
          '& .MuiChip-label': { px: 1.5 },
        }}
      />
    </header>
  );
}
