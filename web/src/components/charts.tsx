"use client";

import { pct, signed, type Cell } from "@/lib/data";

/* ---------------------------------------------------------------- controls */
export function Seg<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <div className="control" role="group" aria-label={label}>
      <span>{label}</span>
      <div className="seg">
        {options.map((o) => (
          <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Select<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: { value: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <label className="control">
      <span>{label}</span>
      <select className="sel" value={value} onChange={(e) => onChange(e.target.value as T)}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}

/* ---------------------------------------------------- grouped rate bars + CI */
export interface BarSeries { key: string; label: string; color: string }
export function RateBars({ groups, series, get, max, title }: {
  groups: string[]; series: BarSeries[]; get: (group: string, key: string) => Cell | undefined; max?: number; title: string;
}) {
  const W = 760, left = 170, right = 70, bh = 18, gap = 5, groupGap = 22;
  const peak = Math.max(...groups.flatMap((g) => series.map((s) => get(g, s.key)?.hi ?? 0)));
  const step = peak <= 20 ? 5 : peak <= 60 ? 10 : 20;
  const top = max ?? Math.max(10, Math.ceil(peak / step) * step);
  const sx = (v: number) => left + (v / top) * (W - left - right);
  const groupH = series.length * (bh + gap) - gap;
  const H = 24 + groups.length * (groupH + groupGap);
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H + 8}`} role="img" aria-label={title}>
      <title>{title}</title>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={sx(t)} x2={sx(t)} y1={4} y2={H - 16} stroke="var(--rule)" />
          <text className="ax" x={sx(t)} y={H} textAnchor="middle">{t}%</text>
        </g>
      ))}
      {groups.map((g, gi) => {
        const y0 = 8 + gi * (groupH + groupGap);
        return (
          <g key={g}>
            <text className="lab" x={0} y={y0 + groupH / 2 + 4} style={{ fontWeight: 600 }}>{g}</text>
            {series.map((s, si) => {
              const c = get(g, s.key);
              if (!c) return null;
              const y = y0 + si * (bh + gap);
              return (
                <g key={s.key}>
                  <rect x={left} y={y} width={Math.max(2, sx(c.rate) - left)} height={bh} rx={2} fill={s.color}>
                    <title>{`${s.label}: ${c.count} of ${c.n} (${pct(c.rate)}, 95% range ${pct(c.lo)} to ${pct(c.hi)})`}</title>
                  </rect>
                  <line x1={sx(c.lo)} x2={sx(c.hi)} y1={y + bh / 2} y2={y + bh / 2} stroke="var(--ink)" strokeOpacity={0.55} strokeWidth={1.5} />
                  <text className="val" x={Math.max(sx(c.rate), sx(c.hi)) + 6} y={y + bh / 2 + 4.5}>{pct(c.rate)}</text>
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}

/* ------------------------------------------------------------------ heatmap */
function mix(t: number, from: [number, number, number], to: [number, number, number]) {
  const c = from.map((f, i) => Math.round(f + (to[i] - f) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
export function Heatmap({ rows, cols, get, title, good = false, colNotes }: {
  rows: string[]; cols: string[]; get: (r: string, c: string) => Cell | undefined; title: string; good?: boolean; colNotes?: Record<string, string>;
}) {
  const W = 760, left = 190, top = colNotes ? 46 : 30, ch = 46;
  const cw = (W - left) / cols.length;
  const vals = rows.flatMap((r) => cols.map((c) => get(r, c)?.rate ?? 0));
  const hi = good ? 100 : Math.max(20, ...vals);
  const base: [number, number, number] = [246, 248, 244];
  const ink: [number, number, number] = good ? [30, 140, 126] : [91, 58, 158];
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${top + rows.length * ch + 4}`} role="img" aria-label={title}>
      <title>{title}</title>
      {cols.map((c, j) => (
        <g key={c}>
          <text className="lab" x={left + j * cw + cw / 2} y={16} textAnchor="middle" style={{ fontWeight: 600 }}>{c}</text>
          {colNotes?.[c] && <text className="ax" x={left + j * cw + cw / 2} y={33} textAnchor="middle">{colNotes[c]}</text>}
        </g>
      ))}
      {rows.map((r, i) => (
        <g key={r}>
          <text className="lab" x={0} y={top + i * ch + ch / 2 + 4} style={{ fontWeight: 600 }}>{r}</text>
          {cols.map((c, j) => {
            const v = get(r, c);
            if (!v) return null;
            const t = Math.min(1, v.rate / hi);
            const dark = t > 0.55;
            return (
              <g key={c}>
                <rect x={left + j * cw + 2} y={top + i * ch + 2} width={cw - 4} height={ch - 4} rx={4} fill={mix(t, base, ink)} stroke="var(--rule-2)">
                  <title>{`${r}, ${c}: ${v.count} of ${v.n} (${pct(v.rate)}, 95% range ${pct(v.lo)} to ${pct(v.hi)})`}</title>
                </rect>
                <text x={left + j * cw + cw / 2} y={top + i * ch + ch / 2 + 1} textAnchor="middle" className="val" style={{ fill: dark ? "#fafbf7" : "var(--ink)" }}>{pct(v.rate, v.rate < 10 ? 1 : 0)}</text>
                <text x={left + j * cw + cw / 2} y={top + i * ch + ch / 2 + 15} textAnchor="middle" className="ax" style={{ fill: dark ? "#e8e2f3" : "var(--muted)", fontSize: 10.5 }}>{v.count}/{v.n}</text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

/* ------------------------------------------------------------- forest plot */
export interface ForestRow { label: string; diff: number; lo: number; hi: number; note?: string }
export function Forest({ rows, title, leftLabel, rightLabel }: {
  rows: ForestRow[]; title: string; leftLabel: string; rightLabel: string;
}) {
  const W = 760, left = 230, right = 190, rh = 34, top = 30;
  const span = Math.max(10, ...rows.flatMap((r) => [Math.abs(r.lo), Math.abs(r.hi)]));
  const lim = Math.ceil(span / 10) * 10;
  const sx = (v: number) => left + ((v + lim) / (2 * lim)) * (W - left - right);
  const H = top + rows.length * rh + 26;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title}>
      <title>{title}</title>
      <text className="ax" x={sx(-lim)} y={14}>{leftLabel}</text>
      <text className="ax" x={sx(lim)} y={14} textAnchor="end">{rightLabel}</text>
      {[-lim, -lim / 2, 0, lim / 2, lim].map((t) => (
        <g key={t}>
          <line x1={sx(t)} x2={sx(t)} y1={top - 6} y2={H - 22} stroke={t === 0 ? "var(--ink)" : "var(--rule)"} strokeDasharray={t === 0 ? "4 3" : undefined} />
          <text className="ax" x={sx(t)} y={H - 6} textAnchor="middle">{t === 0 ? "0" : signed(t, 0)}</text>
        </g>
      ))}
      {rows.map((r, i) => {
        const y = top + i * rh + rh / 2;
        const clear = r.lo > 0 || r.hi < 0;
        const col = r.diff < 0 ? "var(--b)" : r.diff > 0 ? "var(--a)" : "var(--ink-2)";
        return (
          <g key={r.label}>
            <text className="lab" x={0} y={y + 4}>{r.label}</text>
            <line x1={sx(r.lo)} x2={sx(r.hi)} y1={y} y2={y} stroke={col} strokeWidth={2.5} strokeOpacity={clear ? 1 : 0.45} />
            <circle cx={sx(r.diff)} cy={y} r={6} fill={clear ? col : "var(--sheet)"} stroke={col} strokeWidth={2} />
            <text className="val" x={W - right + 14} y={y + 4}>{signed(r.diff)} pts</text>
            {r.note && <text className="ax" x={W - right + 76} y={y + 4}>{r.note}</text>}
          </g>
        );
      })}
    </svg>
  );
}
