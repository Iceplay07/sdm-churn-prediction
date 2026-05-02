import React from "react";
import { html } from "htm/react";
import { useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useAtRisk } from "../api/hooks.js";
import { Header } from "../components/Header.js";
import { Filters } from "../components/Filters.js";
import { ClientsTable } from "../components/ClientsTable.js";
import { EmptyState } from "../components/EmptyState.js";
import { ErrorBanner } from "../components/ErrorBanner.js";
import { Skeleton } from "../components/Skeleton.js";

const DEFAULT_LIMIT = 25;

function readParams(sp) {
  const p = {
    mode: sp.get("mode") || "balanced",
    geography: sp.get("geography") || undefined,
    segment: sp.get("segment") || undefined,
    min_score: sp.get("min_score") ? parseFloat(sp.get("min_score")) : 0,
    sort: sp.get("sort") || "-score",
    limit: sp.get("limit") ? parseInt(sp.get("limit"), 10) : DEFAULT_LIMIT,
    offset: sp.get("offset") ? parseInt(sp.get("offset"), 10) : 0,
  };
  return p;
}
function writeParams(p) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(p)) {
    if (v == null || v === "" || v === 0 || v === undefined) continue;
    sp.set(k, String(v));
  }
  return sp;
}

export function DashboardPage() {
  const [sp, setSp] = useSearchParams();
  const params = readParams(sp);
  const update = (next) => setSp(writeParams(next));

  const apiParams = { ...params, only_at_risk: true };
  const q = useAtRisk(apiParams);
  const data = q.data;

  const total = data?.total ?? 0;
  const pageStart = params.offset + 1;
  const pageEnd = Math.min(params.offset + params.limit, total);
  const canPrev = params.offset > 0;
  const canNext = params.offset + params.limit < total;

  return html`
    <div>
      <${Header} mode=${params.mode} onModeChange=${(m) => update({ ...params, mode: m, offset: 0 })} />

      <main class="max-w-7xl mx-auto px-6 py-6">
        <div class="mb-3">
          <h1 class="text-2xl font-bold text-slate-900">Клиенты в зоне риска</h1>
          <p class="text-sm text-slate-500 mt-1">
            Прогноз ухода в ближайшие 28 дней. Источник:
            <span class="font-medium">CatBoost + SHAP</span> · режим
            <span class="font-mono text-xs px-1.5 py-0.5 bg-slate-100 rounded">${params.mode}</span>
          </p>
        </div>

        <${Filters} value=${params} onChange=${update} />

        ${q.isLoading && html`<${Skeleton} rows=${10} />`}
        ${q.isError && html`
          <${ErrorBanner}
            message=${q.error?.message || "Не удалось загрузить список клиентов"}
            onRetry=${() => q.refetch()}
          />
        `}
        ${data && data.items.length === 0 && html`
          <${EmptyState}
            title="Под фильтр не попал ни один клиент"
            hint="Попробуйте сбросить фильтры или переключить режим на «Широкий охват»."
          />
        `}
        ${data && data.items.length > 0 && html`
          <${React.Fragment}>
            <${ClientsTable}
              items=${data.items}
              sort=${params.sort}
              onSortChange=${(s) => update({ ...params, sort: s, offset: 0 })}
            />

            <div class="mt-4 flex items-center justify-between text-sm text-slate-600">
              <div>
                Показано <span class="font-semibold">${pageStart}–${pageEnd}</span>
                из <span class="font-semibold">${total}</span> клиентов
                <span class="text-slate-400">·</span>
                <span class="text-slate-400">total at-risk: ${total}</span>
              </div>
              <div class="flex items-center gap-2">
                <button
                  disabled=${!canPrev}
                  onClick=${() => update({ ...params, offset: Math.max(0, params.offset - params.limit) })}
                  class="px-2 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-100 inline-flex items-center gap-1"
                >
                  <${ChevronLeft} size=${16} /> Назад
                </button>
                <button
                  disabled=${!canNext}
                  onClick=${() => update({ ...params, offset: params.offset + params.limit })}
                  class="px-2 py-1 rounded border border-slate-300 disabled:opacity-40 hover:bg-slate-100 inline-flex items-center gap-1"
                >
                  Вперёд <${ChevronRight} size=${16} />
                </button>
              </div>
            </div>
          <//>
        `}
      </main>
    </div>
  `;
}
