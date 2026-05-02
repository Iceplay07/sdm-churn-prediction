import { html } from "htm/react";
import { classNames } from "../lib/format.js";

const STYLES = {
  high:   "bg-red-100 text-red-700 ring-red-200",
  medium: "bg-amber-100 text-amber-800 ring-amber-200",
  low:    "bg-emerald-100 text-emerald-700 ring-emerald-200",
};
const LABELS = { high: "Высокий", medium: "Средний", low: "Низкий" };

export function RiskBadge({ level }) {
  const cls = STYLES[level] || "bg-slate-100 text-slate-700 ring-slate-200";
  return html`
    <span class=${classNames(
      "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ring-1 ring-inset",
      cls,
    )}>${LABELS[level] || level}</span>
  `;
}
