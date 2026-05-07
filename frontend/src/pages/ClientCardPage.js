import React from "react";
import { html } from "htm/react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, User, MapPin, CreditCard, Wallet } from "lucide-react";
import { useClient, useTransactions } from "../api/hooks.js";
import { Header } from "../components/Header.js";
import { ScoreGauge } from "../components/ScoreGauge.js";
import { TopFactorsList } from "../components/TopFactorsList.js";
import { OfferCard } from "../components/OfferCard.js";
import { ActivityChart } from "../components/ActivityChart.js";
import { Skeleton } from "../components/Skeleton.js";
import { ErrorBanner } from "../components/ErrorBanner.js";
import { formatRub } from "../lib/format.js";

function ProfileLine({ icon, label, value }) {
  return html`
    <div class="flex items-center gap-2 text-sm">
      <${icon} size=${14} class="text-slate-400" />
      <span class="text-slate-500">${label}:</span>
      <span class="font-medium text-slate-900">${value}</span>
    </div>
  `;
}

export function ClientCardPage() {
  const { id } = useParams();
  const cid = parseInt(id, 10);
  const [sp, setSp] = useSearchParams();
  const mode = sp.get("mode") || "balanced";

  const cq = useClient(cid);
  const tq = useTransactions(cid, 90);
  const c = cq.data;

  return html`
    <div>
      <${Header} mode=${mode} onModeChange=${(m) => { sp.set("mode", m); setSp(sp); }} />

      <main class="max-w-7xl mx-auto px-6 py-6">
        <${Link} to=${{ pathname: "/", search: sp.toString() }} class="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900 mb-4">
          <${ArrowLeft} size=${14} /> Назад к списку
        <//>

        ${cq.isLoading && html`<${Skeleton} rows=${6} />`}
        ${cq.isError && html`<${ErrorBanner} message=${cq.error?.message} onRetry=${() => cq.refetch()} />`}

        ${c && html`
          <${React.Fragment}>
            <div class="bg-white rounded-xl border border-slate-200 p-6 mb-4">
              <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="lg:col-span-2">
                  <div class="flex items-center gap-3 mb-3">
                    <div class="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-600">
                      <${User} size=${24} />
                    </div>
                    <div>
                      <div class="text-2xl font-bold text-slate-900">${c.full_name}</div>
                      <div class="text-xs text-slate-500">ID ${c.client_id} · ${c.age} лет · сегмент ${c.segment}</div>
                    </div>
                  </div>
                  <div class="grid grid-cols-2 gap-x-6 gap-y-1.5 mt-4">
                    <${ProfileLine} icon=${MapPin} label="Регион" value=${c.geography} />
                    <${ProfileLine} icon=${Wallet} label="Зарплата (мес.)" value=${formatRub(c.salary_monthly_rub)} />
                    <${ProfileLine} icon=${CreditCard} label="Продуктов" value=${c.n_products} />
                    <${ProfileLine} icon=${Wallet} label="Остаток на счёте" value=${formatRub(c.balance_rub)} />
                    <${ProfileLine} icon=${User} label="Стаж" value=${`${c.tenure_years} лет`} />
                    <${ProfileLine} icon=${User} label="Активный" value=${c.is_active_member ? "Да" : "Нет"} />
                  </div>
                </div>

                <div class="border-l border-slate-100 pl-6 flex flex-col items-center justify-center">
                  <${ScoreGauge} score=${c.churn_score} level=${c.risk_level} />
                  <div class="text-xs text-slate-500 mt-2">
                    ${c.is_at_risk ? html`<span class="text-red-600 font-medium">В зоне риска</span>` : "Стабилен"}
                  </div>
                </div>
              </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              <div class="bg-white rounded-xl border border-slate-200 p-5">
                <div class="text-sm font-semibold text-slate-900 mb-3">Топ-3 причины риска (SHAP)</div>
                <${TopFactorsList} factors=${c.top_factors} />
              </div>

              <${OfferCard} offer=${c.offer} />
            </div>

            <div class="bg-white rounded-xl border border-slate-200 p-5">
              <div class="flex items-center justify-between mb-3">
                <div class="text-sm font-semibold text-slate-900">Активность за 90 дней</div>
                <div class="text-xs text-slate-500">Транзакций: ${tq.data?.n_transactions ?? "—"}</div>
              </div>
              <${ActivityChart} transactions=${tq.data?.items} isLoading=${tq.isLoading} />
            </div>
          <//>
        `}
      </main>
    </div>
  `;
}
