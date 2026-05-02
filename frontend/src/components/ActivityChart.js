import { html } from "htm/react";
import { useMemo } from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from "recharts";

export function ActivityChart({ transactions, isLoading }) {
  const data = useMemo(() => {
    if (!transactions) return [];
    const byDay = new Map();
    for (const t of transactions) {
      const cur = byDay.get(t.date) || { date: t.date, outflow: 0, inflow: 0, count: 0 };
      if (t.amount_rub < 0) cur.outflow += -t.amount_rub;
      else                   cur.inflow  += t.amount_rub;
      cur.count += 1;
      byDay.set(t.date, cur);
    }
    return Array.from(byDay.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [transactions]);

  if (isLoading) {
    return html`<div class="h-48 bg-slate-100 rounded-lg animate-pulse" />`;
  }
  if (data.length === 0) {
    return html`<div class="h-48 flex items-center justify-center text-sm text-slate-400">Нет транзакций за период</div>`;
  }

  // Маркер «снижение активности» — последняя четверть периода
  const cut = data[Math.floor(data.length * 0.75)]?.date;

  return html`
    <div class="h-56 w-full">
      <${ResponsiveContainer} width="100%" height="100%">
        <${BarChart} data=${data} margin=${{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <${CartesianGrid} stroke="#e2e8f0" strokeDasharray="3 3" vertical=${false} />
          <${XAxis} dataKey="date" tick=${{ fontSize: 10, fill: "#64748b" }} interval="preserveStartEnd" minTickGap=${24} />
          <${YAxis} tick=${{ fontSize: 10, fill: "#64748b" }} tickFormatter=${(v) => v >= 1000 ? `${Math.round(v/1000)}k` : v} />
          <${Tooltip}
            formatter=${(v, name) => [Math.round(v).toLocaleString("ru-RU") + " ₽", name === "outflow" ? "Расходы" : "Поступления"]}
            labelFormatter=${(d) => `Дата: ${d}`}
            contentStyle=${{ fontSize: 12, borderRadius: 8 }}
          />
          ${cut && html`<${ReferenceLine} x=${cut} stroke="#cf1322" strokeDasharray="4 4" label=${{ value: "снижение", position: "top", fill: "#cf1322", fontSize: 10 }} />`}
          <${Bar} dataKey="outflow" fill="#0050b3" radius=${[3, 3, 0, 0]} />
          <${Bar} dataKey="inflow" fill="#13c2c2" radius=${[3, 3, 0, 0]} />
        <//>
      <//>
    </div>
  `;
}
