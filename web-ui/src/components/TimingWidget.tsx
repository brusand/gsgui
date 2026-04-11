import React, { useState, useEffect } from 'react';
import './TimingWidget.css';

type TimingMode = 'now' | 'end' | 'at' | 'next';

interface Parsed {
  mode: TimingMode;
  h: number; m: number; s: number;
  at: string; // HH:MM
}

function parseTiming(value: string): Parsed {
  if (!value || value.trim() === 'now') return { mode: 'now', h: 0, m: 0, s: 0, at: '00:00' };

  const endFull = value.match(/^end-(\d+)h(\d+)m(\d+)s$/);
  if (endFull) return { mode: 'end', h: +endFull[1], m: +endFull[2], s: +endFull[3], at: '00:00' };

  const endHM = value.match(/^end-(\d+)h(\d+)m$/);
  if (endHM) return { mode: 'end', h: +endHM[1], m: +endHM[2], s: 0, at: '00:00' };

  const endM = value.match(/^end-(\d+)m(\d+)s$/);
  if (endM) return { mode: 'end', h: 0, m: +endM[1], s: +endM[2], at: '00:00' };

  const atMatch = value.match(/^at-(\d{2}:\d{2})$/);
  if (atMatch) return { mode: 'at', h: 0, m: 0, s: 0, at: atMatch[1] };

  const nextFull = value.match(/^next-(\d+)h(\d+)m(\d+)s$/);
  if (nextFull) return { mode: 'next', h: +nextFull[1], m: +nextFull[2], s: +nextFull[3], at: '00:00' };

  const nextM = value.match(/^next-(\d+)m(\d+)s$/);
  if (nextM) return { mode: 'next', h: 0, m: +nextM[1], s: +nextM[2], at: '00:00' };

  return { mode: 'now', h: 0, m: 0, s: 0, at: '00:00' };
}

function serializeTiming(p: Parsed): string {
  if (p.mode === 'now') return 'now';
  if (p.mode === 'at') return `at-${p.at}`;
  const h = String(p.h).padStart(2, '0');
  const m = String(p.m).padStart(2, '0');
  const s = String(p.s).padStart(2, '0');
  if (p.mode === 'next') return `next-${h}h${m}m${s}s`;
  return `end-${h}h${m}m${s}s`;
}

interface Props {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}

const TimingWidget: React.FC<Props> = ({ value, onChange, disabled }) => {
  const [p, setP] = useState<Parsed>(() => parseTiming(value));

  useEffect(() => { setP(parseTiming(value)); }, [value]);

  const update = (next: Partial<Parsed>) => {
    const merged = { ...p, ...next };
    setP(merged);
    onChange(serializeTiming(merged));
  };

  return (
    <div className="timing-widget">
      <select
        className="timing-mode"
        value={p.mode}
        disabled={disabled}
        onChange={e => update({ mode: e.target.value as TimingMode })}
      >
        <option value="now">maintenant</option>
        <option value="end">avant fin</option>
        <option value="next">dans</option>
        <option value="at">à heure fixe</option>
      </select>

      {(p.mode === 'end' || p.mode === 'next') && (
        <span className="timing-duration">
          <input type="number" min={0} max={99}  value={p.h} disabled={disabled}
            onChange={e => update({ h: +e.target.value })} />
          <span className="timing-sep">h</span>
          <input type="number" min={0} max={59}  value={p.m} disabled={disabled}
            onChange={e => update({ m: +e.target.value })} />
          <span className="timing-sep">m</span>
          <input type="number" min={0} max={59}  value={p.s} disabled={disabled}
            onChange={e => update({ s: +e.target.value })} />
          <span className="timing-sep">s</span>
        </span>
      )}

      {p.mode === 'at' && (
        <input type="time" className="timing-at" value={p.at} disabled={disabled}
          onChange={e => update({ at: e.target.value })} />
      )}
    </div>
  );
};

export default TimingWidget;
