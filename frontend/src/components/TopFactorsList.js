import { html } from "htm/react";
import { ArrowUp, ArrowDown } from "lucide-react";
import { formatFeatureName } from "../lib/format.js";

function valueLabel(value) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  const n = Number(value);
  if (!isFinite(n)) return String(value);
  if (Math.abs(n) >= 1000) return n.toLocaleString("ru-RU", { maximumFractionDigits: 0 });
  if (Math.abs(n) >= 1)    return n.toFixed(2);
  return n.toFixed(3);
}

export function TopFactorsList({ factors }) {
  if (!factors || factors.length === 0) {
    return html`<div class="text-sm text-slate-400">Факторы недоступны</div>`;
  }

  return html`
    <ol class="space-y-2">
      ${factors.map((f, i) => html`
        <li key=${i} class="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
          <div class=${`w-8 h-8 rounded-full flex items-center justify-center font-semibold text-xs flex-shrink-0
            ${f.direction === "+" ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"}`}>
            ${f.direction === "+" ? html`<${ArrowUp} size=${14} />` : html`<${ArrowDown} size=${14} />`}
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm text-slate-900">${formatFeatureName(f.feature)}</div>
            <div class="text-xs text-slate-500 mt-0.5">
              значение <span class="font-mono text-slate-700">${valueLabel(f.value)}</span>
              <span class="text-slate-300">·</span>
              вклад в риск
              <span class=${`font-mono ${f.impact > 0 ? "text-red-600" : "text-emerald-600"}`}>
                ${f.impact > 0 ? "+" : ""}${f.impact.toFixed(2)}
              </span>
            </div>
          </div>
        </li>
      `)}
    </ol>
  `;
}
