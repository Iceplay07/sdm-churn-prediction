import { html } from "htm/react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, ChevronUp, ChevronDown, ArrowUpDown } from "lucide-react";
import { RiskBadge } from "./RiskBadge.js";

const COLS = [
  { key: "full_name",   label: "Клиент",  sort: "name" },
  { key: "geography",   label: "Регион" },
  { key: "segment",     label: "Сегмент", sort: "segment" },
  { key: "score",       label: "Скор",    sort: "score", numeric: true },
  { key: "risk_level",  label: "Риск" },
  { key: "offer",       label: "Оффер" },
];

function ScoreCell({ value, level }) {
  const colors = { high: "bg-red-500", medium: "bg-amber-500", low: "bg-emerald-500" };
  const pct = Math.round((value || 0) * 100);
  return html`
    <div class="flex items-center gap-2 min-w-[100px]">
      <div class="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div class="h-full ${colors[level] || "bg-slate-400"}" style=${{ width: `${pct}%` }}></div>
      </div>
      <span class="text-xs text-slate-700 tabular-nums w-9 text-right">${pct}%</span>
    </div>
  `;
}

export function ClientsTable({ items, sort, onSortChange }) {
  const navigate = useNavigate();
  const sortKey = sort.replace(/^-/, "");
  const sortDesc = sort.startsWith("-");

  const onHeaderClick = (col) => {
    if (!col.sort) return;
    if (sortKey === col.sort) onSortChange((sortDesc ? "" : "-") + col.sort);
    else onSortChange("-" + col.sort);
  };

  return html`
    <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide">
          <tr>
            ${COLS.map((col) => html`
              <th
                key=${col.key}
                class=${`px-4 py-2.5 text-left ${col.sort ? "cursor-pointer select-none hover:text-slate-900" : ""} ${col.numeric ? "text-right" : ""}`}
                onClick=${() => onHeaderClick(col)}
              >
                <span class="inline-flex items-center gap-1">
                  ${col.label}
                  ${col.sort && sortKey === col.sort
                    ? (sortDesc ? html`<${ChevronDown} size=${12} />` : html`<${ChevronUp} size=${12} />`)
                    : col.sort && html`<${ArrowUpDown} size=${10} class="opacity-30" />`}
                </span>
              </th>
            `)}
            <th class="px-2"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${items.map((c) => html`
            <tr
              key=${c.client_id}
              onClick=${() => navigate(`/clients/${c.client_id}`)}
              class="hover:bg-slate-50 cursor-pointer"
            >
              <td class="px-4 py-2.5">
                <div class="font-medium text-slate-900">${c.full_name}</div>
                <div class="text-[11px] text-slate-500">ID ${c.client_id} · ${c.age} лет</div>
              </td>
              <td class="px-4 py-2.5 text-slate-700">${c.geography}</td>
              <td class="px-4 py-2.5 text-slate-700 capitalize">${c.segment}</td>
              <td class="px-4 py-2.5">
                <${ScoreCell} value=${c.churn_score} level=${c.risk_level} />
              </td>
              <td class="px-4 py-2.5">
                <${RiskBadge} level=${c.risk_level} />
              </td>
              <td class="px-4 py-2.5 text-slate-700 max-w-[280px] truncate" title=${c.offer?.reason}>
                ${c.offer?.title ?? html`<span class="text-slate-400">—</span>`}
              </td>
              <td class="px-2 text-slate-300">
                <${ChevronRight} size=${16} />
              </td>
            </tr>
          `)}
        </tbody>
      </table>
    </div>
  `;
}
