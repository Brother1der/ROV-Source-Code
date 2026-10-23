export type MissionState = 'idle' | 'connecting' | 'running' | 'receiving' | 'complete' | 'error';

export type LogLevel = 'info' | 'success' | 'data' | 'warn' | 'error';

export type DataPoint = {
  t: number;
  d: number;
};

export type LogMessage = {
  time: string;
  text: string;
  level: LogLevel;
};

export type MissionStats = {
  maxDepth?: number;
  duration?: number;
  points?: number;
};

export type ApiStatus = {
  state: MissionState;
  message: string;
  elapsed_seconds: number | null;
};

export type ApiMissionData = {
  depthPoints: DataPoint[];
  stats: { maxDepth: number; duration: number; points: number };
};
