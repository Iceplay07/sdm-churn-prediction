import { html } from "htm/react";

const COLORS = { high: "#cf1322", medium: "#fa8c16", low: "#52c41a" };

export function ScoreGauge({ score, level }) {
  const pct = Math.max(0, Math.min(1, score || 0));
  const angle = -90 + pct * 180;             // полукруг от -90° до +90°
  const r = 70;
  const cx = 90, cy = 90;
  const startX = cx + r * Math.cos(Math.PI);
  const startY = cy + r * Math.sin(Math.PI);
  const endX = cx + r * Math.cos((angle * Math.PI) / 180);
  const endY = cy + r * Math.sin((angle * Math.PI) / 180);
  const largeArc = pct > 0.5 ? 1 : 0;
  const color = COLORS[level] || "#0050b3";

  return html`
    <div class="flex flex-col items-center">
      <svg viewBox="0 0 180 110" class="w-44 h-28">
        <path d="M 20 90 A 70 70 0 0 1 160 90" stroke="#e5e7eb" stroke-width="14" fill="none" stroke-linecap="round" />
        <path
          d=${`M ${startX} ${startY} A ${r} ${r} 0 ${largeArc} 1 ${endX} ${endY}`}
          stroke=${color} stroke-width="14" fill="none" stroke-linecap="round"
        />
        <text x="90" y="80" text-anchor="middle" font-size="28" font-weight="700" fill=${color}>
          ${Math.round(pct * 100)}%
        </text>
        <text x="90" y="100" text-anchor="middle" font-size="11" fill="#64748b">риск оттока</text>
      </svg>
    </div>
  `;
}
