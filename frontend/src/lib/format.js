const FEATURE_NAMES = {
  age: "Возраст",
  gender: "Пол",
  geography: "Регион",
  tenure_years: "Стаж клиента",
  credit_score: "Кредитный скор",
  salary_monthly_rub: "Зарплата (мес.)",
  balance_rub: "Остаток на счёте",
  n_products: "Кол-во продуктов",
  has_credit_card: "Кредитная карта",
  is_active_member: "Активный клиент",

  tx_count_90d: "Транзакций за 90 дн.",
  turnover_outflow_90d: "Расходы за 90 дн.",
  tx_count_30d: "Транзакций за 30 дн.",
  turnover_outflow_30d: "Расходы за 30 дн.",
  turnover_outflow_60d_prev: "Расходы 31–90 дн. (предыдущие)",
  days_since_last_tx: "Дней без транзакций",
  inflow_30d: "Поступления за 30 дн.",
  inflow_60d_prev: "Поступления 31–90 дн.",
  sessions_30d: "Сессий в приложении (30 дн.)",
  sessions_60d_prev: "Сессий в приложении (31–90 дн.)",
  days_since_last_login: "Дней без входа в приложение",
  unsubscribe_count_90d: "Отписки от рассылок (90 дн.)",
  support_tickets_30d: "Обращений в поддержку (30 дн.)",
  push_received_90d: "Push получено (90 дн.)",
  push_opened_90d: "Push открыто (90 дн.)",

  turnover_drop_30d_vs_60d_pct: "Падение оборотов",
  sessions_drop_30d_vs_60d_pct: "Падение активности в приложении",
  push_open_rate_90d: "Открываемость push",
  inflow_drop_pct: "Падение поступлений (зарплата)",

  silent_30d: "«Тихий» клиент (нет активности 30 дн.)",
  is_inactive_recent: "Не заходит в приложение",
  tx_per_session_30d: "Транзакций за сессию",
  cash_buffer_months: "Подушка (месяцев на зарплату)",
  support_per_30d_session: "Жалобы на сессию",
  unsubscribed_flag: "Отписался от рассылок",
  push_silence: "Игнорирует push",
  tx_count_drop_30d_vs_avg: "Падение частоты транзакций",
  outflow_per_tx_30d: "Средний чек (30 дн.)",
  no_inflow_30d: "Нет поступлений (30 дн.)",
};

export const formatFeatureName = (k) => FEATURE_NAMES[k] || k;

export function formatRub(value) {
  if (value == null) return "—";
  const n = Number(value);
  if (!isFinite(n)) return "—";
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 0 }) + " ₽";
}

export function formatPct(value, digits = 1) {
  if (value == null || !isFinite(value)) return "—";
  return (Number(value) * 100).toFixed(digits) + "%";
}

export function formatNumber(v, d = 0) {
  if (v == null || !isFinite(v)) return "—";
  return Number(v).toLocaleString("ru-RU", { maximumFractionDigits: d });
}

export function classNames(...xs) {
  return xs.filter(Boolean).join(" ");
}
