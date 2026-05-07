import { html } from "htm/react";
import { Link } from "react-router-dom";
import { TrendingDown, Activity } from "lucide-react";
import { useInfo, useAtRisk } from "../api/hooks.js";

export function Header({ mode, onModeChange }) {
  const info = useInfo();
  const all = useAtRisk({ mode, limit: 1, only_at_risk: true });
  const msk = useAtRisk({ mode, limit: 1, only_at_risk: true, geography: "Москва" });
  const prem = useAtRisk({ mode, limit: 1, only_at_risk: true, segment: "premium" });

  const stat = (label, q, color) => html`
    <div class="text-right">
      <div class="text-xs text-slate-500">${label}</div>
      <div class="text-2xl font-semibold ${color}">${q.isLoading ? "…" : q.data?.total ?? "—"}</div>
    </div>
  `;

  return html`
    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
        <${Link} to="/" class="flex items-center gap-3 hover:opacity-80">
          <div class="w-9 h-9 rounded-lg bg-sdm-primary text-white flex items-center justify-center">
            <${TrendingDown} size=${20} />
          </div>
          <div>
            <div class="font-semibold text-slate-900 leading-tight">ИИ-Маркетолог</div>
            <div class="text-xs text-slate-500">СДМ Банк · прогноз оттока</div>
          </div>
        <//>

        <div class="flex items-center gap-6">
          ${stat("В зоне риска", all, "text-sdm-danger")}
          ${stat("Москва", msk, "text-slate-700")}
          ${stat("Premium", prem, "text-slate-700")}

          <div class="flex flex-col items-start gap-1">
            <label class="text-[10px] text-slate-500 uppercase tracking-wide">Режим порога</label>
            <select
              value=${mode}
              onChange=${(e) => onModeChange(e.target.value)}
              class="text-sm border border-slate-300 rounded-md px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-sdm-primary"
            >
              <option value="balanced">Сбалансированный (P=76%)</option>
              <option value="high_precision">Высокая точность (P≥75%)</option>
              <option value="high_recall">Широкий охват (R≥70%)</option>
            </select>
          </div>

          <div class="flex items-center gap-1 text-xs text-slate-500">
            <${Activity} size=${14} />
            <span>v${info.data?.model_version ?? "1.0"}</span>
          </div>
        </div>
      </div>
    </header>
  `;
}
