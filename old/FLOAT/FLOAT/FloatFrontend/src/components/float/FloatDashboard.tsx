import { useState, useEffect, useRef, useCallback, type JSX } from 'react';
import type { MissionState, DataPoint, LogMessage, MissionStats } from '../../types/mission';
import { getNow, apiStartMission, apiGetStatus, apiGetData } from '../../services/missionService';
import Header from './Header';
import DepthGraph from './DepthGraph';
import OutputLog from './OutputLog';
import MissionControl from './MissionControl';

export default function FloatDashboard(): JSX.Element {
  const [missionState, setMissionState] = useState<MissionState>('idle');
  const [dataPoints, setDataPoints]     = useState<DataPoint[]>([]);
  const [messages, setMessages]         = useState<LogMessage[]>([]);
  const [stats, setStats]               = useState<MissionStats>({});

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Stores the last MissionState seen by the poller to detect transitions
  const tRef = useRef<MissionState>('idle');

  const addMsg = useCallback((text: string, level: LogMessage['level'] = 'info') => {
    setMessages(prev => [...prev, { time: getNow(), text, level }]);
  }, []);

  const stopPolling = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startMission = useCallback(() => {
    setMissionState('connecting');
    setDataPoints([]);
    setMessages([]);
    setStats({});
    tRef.current = 'connecting';

    addMsg('Sending start signal to float…', 'info');

    apiStartMission().catch((err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      addMsg(`Failed to start mission: ${msg}`, 'error');
      setMissionState('error');
      tRef.current = 'error';
    });

    // Poll status every 3 seconds. Single network failures log as warn and keep polling
    // because the Pi's radio loop can briefly block Flask request handling.
    timerRef.current = setInterval(() => {
      apiGetStatus()
        .then(status => {
          const prev = tRef.current;
          const next = status.state;

          if (next !== prev) {
            tRef.current = next;
            setMissionState(next);

            if (next === 'running') {
              addMsg('Lakeview Subaquatics Float — float mission started', 'success');
            } else if (next === 'receiving') {
              addMsg('Lakeview Subaquatics Float - Float has surfaced — data packets arriving…', 'info');
            } else if (next === 'complete') {
              stopPolling();
              addMsg('Lakeview Subaquatics Float - Transmission complete — fetching data…', 'success');
              apiGetData()
                .then(data => {
                  setDataPoints(data.depthPoints);
                  setStats({
                    maxDepth: data.stats.maxDepth,
                    duration: data.stats.duration,
                    points:   data.stats.points,
                  });
                  addMsg(
                    `Data loaded — ${data.stats.points} records, max depth ${data.stats.maxDepth.toFixed(2)} m`,
                    'data',
                  );
                  addMsg('Float ready for recovery.', 'info');
                })
                .catch((err: unknown) => {
                  const msg = err instanceof Error ? err.message : 'Unknown error';
                  addMsg(`Failed to load data: ${msg}`, 'error');
                  setMissionState('error');
                  tRef.current = 'error';
                });
            } else if (next === 'error') {
              stopPolling();
              addMsg(status.message, 'error');
            }
          }
        })
        .catch((err: unknown) => {
          const msg = err instanceof Error ? err.message : 'Unknown error';
          addMsg(`Status poll failed: ${msg}`, 'warn');
        });
    }, 3000);
  }, [addMsg, stopPolling]);

  const resetMission = useCallback(() => {
    stopPolling();
    setMissionState('idle');
    setDataPoints([]);
    setMessages([]);
    setStats({});
    tRef.current = 'idle';
  }, [stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const maxDepth = dataPoints.length ? Math.max(...dataPoints.map(p => p.d)) : 0;

  return (
    <div className="min-h-screen flex flex-col bg-[#EBF5F4]">
      <Header missionState={missionState} />
      <main className="flex-1 w-full max-w-3xl mx-auto px-3 py-4 flex flex-col gap-4">
        <MissionControl
          missionState={missionState}
          onStart={startMission}
          onReset={resetMission}
          stats={stats}
        />
        <DepthGraph dataPoints={dataPoints} maxDepth={maxDepth} missionState={missionState} />
        <OutputLog messages={messages} />
      </main>
      <footer className="text-center py-3 text-xs text-[#6B9E9B]">
        Lakeview Sub-Aquatics · Float v1.0 · 2026
      </footer>
    </div>
  );
}
