import { html } from "htm/react";
import { useState } from "react";
import { Gift, Zap, CheckCircle2 } from "lucide-react";

export function OfferCard({ offer }) {
  const [launched, setLaunched] = useState(false);
  if (!offer) {
    return html`
      <div class="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-slate-500 text-sm">
        У клиента нет рекомендованного оффера
      </div>
    `;
  }

  return html`
    <div class="rounded-xl border border-sdm-primary/30 bg-gradient-to-br from-blue-50 to-cyan-50 p-5">
      <div class="flex items-start gap-3">
        <div class="w-10 h-10 rounded-lg bg-sdm-primary text-white flex items-center justify-center flex-shrink-0">
          <${Gift} size=${20} />
        </div>
        <div class="flex-1">
          <div class="text-xs text-sdm-primary font-medium uppercase tracking-wide">Рекомендованный оффер</div>
          <div class="font-semibold text-slate-900 mt-0.5">${offer.title}</div>
          <div class="text-sm text-slate-600 mt-2 leading-snug">${offer.reason}</div>

          <div class="flex items-center gap-4 mt-3 text-xs">
            <div class="flex items-center gap-1 text-emerald-700">
              <${Zap} size=${14} />
              <span>Ожидаемый lift удержания: <strong>+${Math.round(offer.estimated_lift * 100)}%</strong></span>
            </div>
          </div>

          <div class="mt-4">
            ${launched ? html`
              <div class="inline-flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg border border-emerald-200">
                <${CheckCircle2} size=${16} />
                Кампания запущена
              </div>
            ` : html`
              <button
                onClick=${() => setLaunched(true)}
                class="inline-flex items-center gap-2 bg-sdm-primary hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg shadow-sm transition"
              >
                ${offer.cta}
              </button>
            `}
          </div>
        </div>
      </div>
    </div>
  `;
}
