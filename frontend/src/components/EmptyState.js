import { html } from "htm/react";
import { Inbox } from "lucide-react";

export function EmptyState({ title = "Ничего не найдено", hint }) {
  return html`
    <div class="flex flex-col items-center justify-center py-16 text-slate-400">
      <${Inbox} size=${48} strokeWidth=${1.5} />
      <div class="mt-3 text-sm font-medium text-slate-600">${title}</div>
      ${hint && html`<div class="mt-1 text-xs">${hint}</div>`}
    </div>
  `;
}
