import { useEffect, useRef, type JSX } from 'react';
import type { LogMessage, LogLevel } from '../../types/mission';

type Props = {
  messages: LogMessage[];
};

const LEVEL_COLOR: Record<LogLevel, string> = {
  error:   '#F87171',
  warn:    '#FBBF24',
  success: '#34D399',
  data:    '#7EC8C4',
  info:    '#A3C4C2',
};

const LEVEL_ICON: Record<LogLevel, string> = {
  error:   'fa-circle-xmark',
  warn:    'fa-triangle-exclamation',
  success: 'fa-circle-check',
  data:    'fa-wave-square',
  info:    'fa-angle-right',
};

export default function OutputLog({ messages }: Props): JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (bottomRef.current?.parentElement) {
      bottomRef.current.parentElement.scrollTop = bottomRef.current.offsetTop;
    }
  }, [messages]);

  return (
    <div className="rounded-xl border overflow-hidden flex flex-col border-[#C8E0DF]">
      <div className="px-4 py-2.5 flex items-center gap-2 border-b flex-shrink-0 bg-[#1B6B68] border-[#2D8B84]">
        <i className="fa-solid fa-terminal text-sm text-[#7EC8C4]" />
        <span className="font-medium text-sm tracking-wide uppercase text-[#E0F4F3]"
          style={{ letterSpacing: '0.04em' }}>
          Output Log
        </span>
        <span className="ml-auto text-xs font-mono px-2 py-0.5 rounded bg-[#0D2B2A] text-[#7EC8C4]">
          {messages.length} msgs
        </span>
      </div>

      <div className="overflow-y-auto flex-1 p-3 flex flex-col gap-1 bg-[#0D1F1E]"
        style={{ minHeight: 180, maxHeight: 280, fontFamily: 'monospace' }}>
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-[#2D5E5A]">
            Awaiting device connection…
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className="flex items-start gap-2 text-xs leading-relaxed">
              <span className="flex-shrink-0 w-[72px] font-mono opacity-50 pt-0.5 text-[#7EC8C4]">
                {msg.time}
              </span>
              <i
                className={`fa-solid ${LEVEL_ICON[msg.level]} flex-shrink-0 mt-0.5`}
                style={{ color: LEVEL_COLOR[msg.level], fontSize: 10 }}
              />
              <span style={{ color: LEVEL_COLOR[msg.level] }}>{msg.text}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-3 py-1.5 flex items-center gap-2 border-t bg-[#0F2726] border-[#1B3E3C]">
        <span style={{ color: '#2D8B84', fontFamily: 'monospace', fontSize: 12 }}>▶</span>
        <span className="text-xs animate-pulse text-[#2D5E5A]" style={{ fontFamily: 'monospace' }}>_</span>
      </div>
    </div>
  );
}
