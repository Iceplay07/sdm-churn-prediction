import { html } from "htm/react";
import { AlertCircle, RefreshCw } from "lucide-react";

export function ErrorBanner({ message, onRetry }) {
  return html`
    <div class="rounded-lg border border-red-200 bg-red-50 p-4 flex items-start gap-3">
      <${AlertCircle} class="text-red-500 mt-0.5" size=${20} />
      <div class="flex-1">
        <div class="text-sm font-medium text-red-800">Ошибка загрузки</div>
        <div class="text-xs text-red-700 mt-1">${message}</div>
      </div>
      ${onRetry && html`
        <button
          onClick=${onRetry}
          class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-300 hover:bg-red-100"
        >
          <${RefreshCw} size=${14} /> Повторить
        </button>
      `}
    </div>
  `;
}
