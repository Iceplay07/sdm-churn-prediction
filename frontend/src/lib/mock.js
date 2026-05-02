// Запасной набор данных, чтобы фронт работал когда бэкенд лежит.
// Включается параметрами window.__SDM_USE_MOCK__ или window.__SDM_FALLBACK_ON_ERROR__.

const MOCK_CLIENTS = [
  {
    client_id: 6423, full_name: "Дарья Иванова", age: 34, gender: "F",
    geography: "Москва", tenure_years: 2, n_products: 1, balance_rub: 12000,
    salary_monthly_rub: 95000, is_active_member: 0, segment: "basic",
    churn_score: 0.996, churn_probability_pct: 100, risk_level: "high", is_at_risk: true,
    top_factors: [
      { feature: "support_tickets_30d", value: 2, impact: 1.52, direction: "+" },
      { feature: "unsubscribe_count_90d", value: 1, impact: 0.84, direction: "+" },
      { feature: "days_since_last_login", value: 21, impact: 0.66, direction: "+" },
    ],
    offer: { id: "manager_call", title: "Звонок персонального менеджера",
             reason: "У клиента 2 обращений в поддержку за 30 дней — фрустрация",
             estimated_lift: 0.22, cta: "Запланировать звонок на завтра" },
  },
  {
    client_id: 2230, full_name: "Ирина Зайцева", age: 41, gender: "F",
    geography: "Санкт-Петербург", tenure_years: 5, n_products: 2, balance_rub: 230000,
    salary_monthly_rub: 140000, is_active_member: 1, segment: "standard",
    churn_score: 0.95, churn_probability_pct: 95, risk_level: "high", is_at_risk: true,
    top_factors: [
      { feature: "inflow_drop_pct", value: 1.0, impact: 1.21, direction: "+" },
      { feature: "no_inflow_30d", value: 1, impact: 0.55, direction: "+" },
      { feature: "n_products", value: 2, impact: -0.10, direction: "-" },
    ],
    offer: { id: "salary_bonus", title: "+1% к вкладу за перевод зарплаты",
             reason: "Зарплата перестала поступать (упала на 100%)",
             estimated_lift: 0.28, cta: "Push-предложение перевести зарплату" },
  },
  {
    client_id: 3730, full_name: "Наталья Богданова", age: 28, gender: "F",
    geography: "Регион", tenure_years: 1, n_products: 1, balance_rub: 8500,
    salary_monthly_rub: 65000, is_active_member: 0, segment: "basic",
    churn_score: 0.91, churn_probability_pct: 91, risk_level: "high", is_at_risk: true,
    top_factors: [
      { feature: "days_since_last_login", value: 28, impact: 1.05, direction: "+" },
      { feature: "sessions_drop_30d_vs_60d_pct", value: 0.95, impact: 0.78, direction: "+" },
      { feature: "balance_rub", value: 8500, impact: 0.18, direction: "+" },
    ],
    offer: { id: "app_reactivation_gift", title: "Бонус 500 ₽ за вход в приложение",
             reason: "Не заходил в приложение 28 дней",
             estimated_lift: 0.15, cta: "Push: подарок на главном экране" },
  },
];

export function mockInfo() {
  return {
    model_version: "1.0",
    trained_at: new Date().toISOString(),
    n_features: 39,
    thresholds: {
      balanced:        { threshold: 0.7757, precision: 0.766, recall: 0.628, f1: 0.690 },
      high_precision:  { threshold: 0.7747, precision: 0.756, recall: 0.628, f1: 0.686 },
      high_recall:     { threshold: 0.6724, precision: 0.623, recall: 0.702, f1: 0.660 },
    },
    default_mode: "balanced",
  };
}

export function mockAtRisk(params = {}) {
  let items = MOCK_CLIENTS.slice();
  if (params.geography) items = items.filter((c) => c.geography === params.geography);
  if (params.segment)   items = items.filter((c) => c.segment === params.segment);
  if (params.min_score) items = items.filter((c) => c.churn_score >= params.min_score);
  items.sort((a, b) => b.churn_score - a.churn_score);
  const limit = params.limit ?? 50;
  const offset = params.offset ?? 0;
  return {
    total: items.length,
    returned: Math.min(limit, items.length - offset),
    mode: params.mode ?? "balanced",
    items: items.slice(offset, offset + limit),
  };
}

export function mockClient(id) {
  const c = MOCK_CLIENTS.find((x) => x.client_id === Number(id));
  if (!c) throw new Error(`Mock 404 for ${id}`);
  return c;
}

export function mockTransactions(id, nDays = 90) {
  const today = new Date();
  const tx = [];
  for (let d = 0; d < nDays; d++) {
    const date = new Date(today);
    date.setDate(today.getDate() - d);
    const wasActive = d > 25;
    const n = wasActive ? Math.floor(Math.random() * 4) : (Math.random() < 0.4 ? 1 : 0);
    for (let i = 0; i < n; i++) {
      tx.push({
        date: date.toISOString().slice(0, 10),
        amount_rub: -Math.round(500 + Math.random() * 5000),
        category: ["grocery", "transport", "online_shopping", "restaurants"][i % 4],
      });
    }
    if (d % 30 === 0 && wasActive) {
      tx.push({
        date: date.toISOString().slice(0, 10),
        amount_rub: 95000,
        category: "transfer_in",
      });
    }
  }
  return { client_id: Number(id), n_days: nDays, n_transactions: tx.length, items: tx };
}
