# SDM Churn — Frontend (Дашборд)

Дашборд маркетолога СДМ Банка на **React 18 + react-query + Recharts + Tailwind**.

## Запуск (без сборки)

Стек подключается через ESM CDN — никакой `npm install` не требуется.
Достаточно поднять любой статический http-server из этой папки:

```bash
# из frontend/
python3 -m http.server 5173
# или
npx --yes serve -p 5173
```

Откройте http://localhost:5173 — фронт ходит в `http://localhost:8000` (FastAPI бэкенд).

## Конфигурация

В `index.html` можно переопределить базовый URL API и mock-режимы:

```html
<script>
  window.__SDM_API_URL__ = "http://localhost:8000";   // куда ходить
  window.__SDM_USE_MOCK__ = false;                    // принудительно использовать mock
  window.__SDM_FALLBACK_ON_ERROR__ = true;            // на ошибке API — на mock (для демо)
</script>
```

## Структура

```
frontend/
├── index.html                  importmap CDN + Tailwind + точка входа
├── src/
│   ├── main.js                 createRoot + Router + QueryClient
│   ├── App.js                  Routes
│   ├── api/
│   │   ├── client.js           axios instance
│   │   └── hooks.js            useInfo / useAtRisk / useClient / useTransactions
│   ├── lib/
│   │   ├── format.js           formatRub, formatPct, formatFeatureName
│   │   └── mock.js             запасные данные для оффлайн-разработки
│   ├── components/             RiskBadge, ScoreGauge, Filters, ClientsTable, ...
│   └── pages/
│       ├── DashboardPage.js    список клиентов в зоне риска
│       └── ClientCardPage.js   карточка клиента + offer + chart
└── public/                     favicon + demo_clients.json
```

## Production-сборка

Один из вариантов перевода в полноценный Vite-build (когда будет время):

```bash
npm create vite@latest frontend-vite -- --template react
# скопировать src/, заменить .js на .jsx, заменить htm-теги на JSX
```

Для хакатонного демо CDN-вариант надёжнее — нет рисков с ESM-разрешением и установкой пакетов.

## Демо-сценарий

См. `STAGE4_FRONTEND_PLAN.md`, секция 5.
