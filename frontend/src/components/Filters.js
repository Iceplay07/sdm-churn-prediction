import { html } from "htm/react";
import { Filter, X } from "lucide-react";

export function Filters({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v, offset: 0 });
  const clear = () => onChange({ mode: value.mode, sort: value.sort, limit: value.limit, offset: 0 });
  const hasFilters = value.geography || value.segment || (value.min_score && value.min_score > 0);

  return html`
    <div class="bg-white rounded-xl border border-slate-200 p-4 mb-4 flex flex-wrap items-end gap-4">
      <div class="flex items-center gap-2 text-sm text-slate-700">
        <${Filter} size=${16} />
        <span class="font-medium">Фильтры</span>
      </div>

      <div>
        <label class="block text-[10px] text-slate-500 uppercase tracking-wide mb-1">Регион</label>
        <select
          value=${value.geography ?? ""}
          onChange=${(e) => set("geography", e.target.value || undefined)}
          class="text-sm border border-slate-300 rounded-md px-2 py-1.5 bg-white"
        >
          <option value="">Любой</option>
          <option value="Москва">Москва</option>
          <option value="Санкт-Петербург">Санкт-Петербург</option>
          <option value="Регион">Регион</option>
        </select>
      </div>

      <div>
        <label class="block text-[10px] text-slate-500 uppercase tracking-wide mb-1">Сегмент</label>
        <select
          value=${value.segment ?? ""}
          onChange=${(e) => set("segment", e.target.value || undefined)}
          class="text-sm border border-slate-300 rounded-md px-2 py-1.5 bg-white"
        >
          <option value="">Любой</option>
          <option value="premium">Premium</option>
          <option value="standard">Standard</option>
          <option value="basic">Basic</option>
        </select>
      </div>

      <div class="min-w-[200px]">
        <label class="block text-[10px] text-slate-500 uppercase tracking-wide mb-1">
          Мин. скор: ${Math.round((value.min_score || 0) * 100)}%
        </label>
        <input
          type="range" min="0" max="0.99" step="0.01"
          value=${value.min_score ?? 0}
          onChange=${(e) => set("min_score", parseFloat(e.target.value))}
          class="w-full"
        />
      </div>

      ${hasFilters && html`
        <button
          onClick=${clear}
          class="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
        >
          <${X} size=${14} /> Сбросить фильтры
        </button>
      `}
    </div>
  `;
}
