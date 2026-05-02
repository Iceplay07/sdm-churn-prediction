import { html } from "htm/react";

export function Skeleton({ rows = 6 }) {
  return html`
    <div class="space-y-2 animate-pulse">
      ${Array.from({ length: rows }).map((_, i) => html`
        <div key=${i} class="h-12 bg-slate-200 rounded-lg" />
      `)}
    </div>
  `;
}
