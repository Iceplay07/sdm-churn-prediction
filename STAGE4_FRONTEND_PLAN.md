# Этап 4 — Дашборд и демо. План выполнения

> Часы 8–16 по общему графику хакатона.
> Ответственные: **Антон** (основной, frontend). **Самир** — помощь на интеграции (часы 13–14). Вся команда — отбор демо-клиентов (час 14–15).

## 0. Что уже готово на старте этапа

API живой и стабильный (Этап 3, 23/23 теста зелёные). Антону **не нужно ничего согласовывать** — Swagger по `/docs` сразу показывает контракт.

| Эндпоинт | Что возвращает | Где использовать |
|---|---|---|
| `GET /info` | Метаданные модели + 3 пресета порога | Header + переключатель режима |
| `GET /clients/at-risk` | Список с офферами (416 клиентов в balanced) | Главный экран дашборда |
| `GET /clients/{id}` | Карточка клиента с top_factors + offer | Страница клиента |
| `GET /clients/{id}/transactions?n_days=90` | История транзакций | График активности |
| `GET /offers/templates` | 8 шаблонов офферов | Опционально — отдельная страница «Каталог офферов» |
| `POST /predict` | Скор для произвольного клиента | Опционально — «What-if» песочница |

CORS уже открыт на `http://localhost:3000` и `http://localhost:5173`.

В `docker-compose.yml` корневом уже **зарезервирован** сервис `frontend` закомментированным блоком — раскомментировать когда Dockerfile готов.

## 1. Стек

| Слой | Технология | Почему именно это |
|---|---|---|
| Bundler | **Vite + React 18 (JS)** | `npm create vite@latest -- --template react`, старт за 30 сек. TS-вариант берём только если останется час. |
| Стили | **Tailwind CSS** | Быстрая прототипизация, без отдельных .css. `npx tailwindcss init -p`. |
| HTTP | **axios** + **@tanstack/react-query** | Кэш, авто-рефетч, loading/error состояния из коробки. |
| Routing | **react-router-dom v6** | Двух-страничный роутинг (`/` + `/clients/:id`). |
| Графики | **Recharts** | Под React, AreaChart/BarChart за 5 строк. |
| UI-кит | **lucide-react** иконки + Tailwind-классы | Без тяжёлой UI-библиотеки. shadcn/ui — опционально, если знаком. |
| Form/state | **React useState/useReducer** | Не тянем Redux, не нужен. |

Установка одной командой:

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install axios @tanstack/react-query react-router-dom recharts lucide-react
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

## 2. Структура папок

```
frontend/
├── public/
├── src/
│   ├── api/
│   │   ├── client.js              axios-инстанс с baseURL
│   │   └── hooks.js               useAtRisk, useClient, useTransactions, useInfo (react-query)
│   ├── components/
│   │   ├── Header.jsx             Логотип + переключатель mode + общая статистика
│   │   ├── Filters.jsx            geography / segment / min_score / mode
│   │   ├── ClientsTable.jsx       Таблица с сортировкой и пагинацией
│   │   ├── RiskBadge.jsx          Цветной бейдж low/medium/high
│   │   ├── ScoreGauge.jsx         Полукруглый индикатор 0..100
│   │   ├── TopFactorsList.jsx     SHAP-факторы с цветом по direction
│   │   ├── OfferCard.jsx          Карточка оффера + CTA-кнопка
│   │   ├── ActivityChart.jsx      Recharts по транзакциям
│   │   ├── EmptyState.jsx         Пустая таблица / нет клиента
│   │   └── ErrorBanner.jsx        Падение API
│   ├── pages/
│   │   ├── DashboardPage.jsx      «/»
│   │   └── ClientCardPage.jsx     «/clients/:id»
│   ├── lib/
│   │   ├── format.js              formatRub, formatPct, formatFeatureName
│   │   └── mock.js                Мок-ответы /clients/at-risk и /clients/:id для офлайн-разработки
│   ├── App.jsx                    Routes + QueryClientProvider
│   ├── main.jsx
│   └── index.css                  @tailwind base/components/utilities
├── .env.development               VITE_API_URL=http://localhost:8000
├── .env.production                VITE_API_URL=http://backend:8000  (для docker-compose)
├── Dockerfile
├── nginx.conf                     для отдачи build из nginx
├── package.json
└── vite.config.js
```

## 3. Подзадачи и тайминг (часы 8–16 = 8 часов)

### 3.1 Setup проекта (≈30 мин, часы 8:00–8:30) — Антон

- `npm create vite@latest frontend -- --template react` + установка пакетов из секции 1.
- Tailwind: `tailwind.config.js` с `content: ["./index.html","./src/**/*.{js,jsx}"]`.
- В `index.css` подключить `@tailwind base/components/utilities`.
- В `vite.config.js` добавить `server.port = 5173`.
- Smoke: `npm run dev`, открывается белый экран с «SDM Churn Dashboard».

### 3.2 API-клиент + react-query (≈30 мин, часы 8:30–9:00) — Антон

- `src/api/client.js`:
  ```js
  import axios from "axios";
  export const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
    timeout: 10000,
  });
  ```
- `src/api/hooks.js` — обёртки над `useQuery`:
  - `useInfo()` → `/info`
  - `useAtRisk(filters)` → `/clients/at-risk` с параметрами
  - `useClient(id)` → `/clients/{id}`
  - `useTransactions(id, nDays=90)` → `/clients/{id}/transactions`
- В `App.jsx` обернуть всё в `QueryClientProvider`.
- **Mock fallback**: если `VITE_API_URL` не задан или возвращает 503, импортировать данные из `lib/mock.js`. Антон не блокируется, если бэкенд лёг.

### 3.3 Dashboard главная (≈90 мин, часы 9:00–10:30) — Антон

Layout:

```
┌─────────────────────────────────────────────────────────┐
│ Header: «ИИ-Маркетолог СДМ»  [mode▼ balanced]  M:145 P:101│
├─────────────────────────────────────────────────────────┤
│ Filters: [Geography▼] [Segment▼] [min_score: ──●──] [⟳]  │
├─────────────────────────────────────────────────────────┤
│ ClientsTable                                             │
│ ┌─ID──┬─Имя─────────┬─Регион─┬─Score─┬─Risk─┬─Offer──┐ │
│ │6423 │Дарья Иванова│Москва  │ 99.6% │[high]│Звонок..│ │
│ │ ... │             │        │       │      │        │ │
│ └─────┴─────────────┴────────┴───────┴──────┴────────┘ │
│  ◀ 1 2 3 ... 9 ▶   showing 1–50 of 416                  │
└─────────────────────────────────────────────────────────┘
```

Компоненты:

- **Header.jsx**: логотип + бейдж режима (`mode`) + 3 числа сверху: «Всего в зоне риска», «В Москве», «Premium-сегмент». Берёт данные из `useAtRisk({limit: 1})` (только `total`) и `useInfo()`.
- **Filters.jsx**: контролируемые `<select>` для `geography` (Москва/СПб/Регион/—), `segment` (premium/standard/basic/—), `<input type="range">` для `min_score`, `<select>` для `mode`. На каждое изменение — обновлять параметры в URL через `useSearchParams`, чтобы фильтры не терялись при F5.
- **ClientsTable.jsx**: 6 колонок, клик по строке → `navigate(/clients/{id})`. Сортировка по клику на header (мутирует параметр `sort`). Пагинация — две кнопки `◀ ▶` + индикатор, на хакатон достаточно.
- **RiskBadge.jsx**: `low` зелёный, `medium` жёлтый, `high` красный. Простой Tailwind-класс.

Готовый к концу часа 10:30: таблица показывает реальные данные из API, фильтры работают, клик ведёт на /clients/:id (даже если страница пока пустая).

### 3.4 Client Card (≈90 мин, часы 10:30–12:00) — Антон

Layout:

```
┌─────────────────────────────────────────────────────────┐
│ ← Назад                                                  │
│                                                          │
│ Дарья Иванова, 34, Москва                                │
│ ┌──────────────┐  ┌─────────────────────────────────┐  │
│ │ ScoreGauge   │  │ Top-3 причины риска              │  │
│ │   99.6%      │  │ ▲ support_tickets_30d=2 (+1.52)  │  │
│ │   [HIGH]     │  │ ▲ unsubscribe_count_90d=1(+0.84) │  │
│ │              │  │ ▼ n_products=3 (-0.22)           │  │
│ └──────────────┘  └─────────────────────────────────┘  │
│                                                          │
│ ┌─ ActivityChart ────────────────────────────────────┐  │
│ │ │█│█│█│ ▏▏  ▏    ↓ резкое падение последние 3 нед. │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ┌─ OfferCard ────────────────────────────────────────┐  │
│ │ Звонок персонального менеджера                      │  │
│ │ Причина: 2 обращения в поддержку за 30 дней         │  │
│ │ Ожидаемый lift: +22%                                │  │
│ │  [ Запустить кампанию ]                              │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

Компоненты:

- **ScoreGauge.jsx**: SVG-полукольцо, цвет = risk_level. ~30 строк, можно «полу-CSS» через `conic-gradient`.
- **TopFactorsList.jsx**: для каждого фактора — стрелка ▲ (direction +) или ▼ (direction -), читаемое имя (`support_tickets_30d` → «Обращений в поддержку»), значение, impact. Таблица `lib/format.js::formatFeatureName` превращает snake_case в человеко-читаемое.
- **ActivityChart.jsx**: `useTransactions(id)` → группируем по дням (Recharts `BarChart`, X = дата, Y = `|amount_rub|`). Можно две серии: расходы/поступления (цвет). Добавить вертикальную линию-маркер «снижение активности» если есть.
- **OfferCard.jsx**: title + reason + estimated_lift + большая CTA-кнопка. По нажатию — `alert("Кампания #12345 запущена")` (на демо больше ничего не нужно).

Готовый к концу 12:00: страница карточки полностью работает с реальным API.

### 3.5 Routing + Header + общий polish (≈60 мин, часы 12:00–13:00) — Антон

- React Router: `BrowserRouter`, `Routes` с `/` и `/clients/:id`.
- В Header — кнопка «Назад к списку» на странице карточки.
- `EmptyState.jsx` для случая когда фильтры дают 0 строк («Нет клиентов под фильтр — попробуйте режим high_recall»).
- `ErrorBanner.jsx` для случая когда API лежит.
- Loading skeletons (Tailwind `animate-pulse`).

### 3.6 E2E проверка с Самиром (≈60 мин, часы 13:00–14:00) — Антон + Самир

- Поднять backend (`make run`), фронт (`npm run dev`), пройти **полный сценарий** из секции 7:
  1. Открыть дашборд → видим 416 клиентов
  2. Применить фильтр «Москва» → 145 клиентов
  3. Кликнуть на топового → карточка с factors + chart + offer
  4. Нажать CTA офера → alert
  5. Назад → дашборд → переключить mode на high_recall → больше клиентов
- Логировать все ошибки/несоответствия. Самир чинит со стороны API, Антон — со стороны UI.
- Если что-то некритичное (косметика) — записать в `KNOWN_ISSUES.md`, не чинить.

### 3.7 Демо-данные: подбор 5–10 «живых» клиентов (≈45 мин, часы 14:00–14:45) — Вся команда

Цель: на демо у нас должны быть клиенты с **разными профилями и разными офферами**, чтобы жюри увидел разнообразие сигналов.

Скрипт `scripts/pick_demo_clients.py` (Самир/Миша) — выбирает по одному клиенту для каждого типа оффера:

```python
# 5 разных офферов = 5 хороших примеров для демо
target_offers = ["manager_call", "comm_resettings", "salary_bonus",
                 "cashback_grocery_5pct", "app_reactivation_gift"]
+ один loyal клиент (low risk, для контраста)
```

Сохраняем `demo_clients.json` в `frontend/public/` — Антон может в Header добавить кнопку «🎬 Демо-режим» которая фильтрует таблицу до этих ID.

### 3.8 Frontend Dockerfile + интеграция в docker-compose (≈30 мин, часы 14:45–15:15) — Антон

Multi-stage build:

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

`nginx.conf` — простой `try_files $uri /index.html;` для SPA-роутинга.

В корневом `docker-compose.yml` раскомментировать сервис `frontend`, исправить порт `3000:80`, проверить что `VITE_API_URL=http://localhost:8000` (билд-тайм env, в Vite через `define` или build args).

`docker compose up --build` → оба сервиса живые.

### 3.9 Финальный polish и репетиция (≈45 мин, часы 15:15–16:00) — Антон + вся команда

- Loading-состояния на каждый запрос (`{isLoading && <Skeleton/>}`).
- Error-состояния на каждый запрос (с кнопкой «Повторить»).
- Пустые состояния (нет клиентов под фильтр, клиент не найден).
- Базовая адаптивность — на ноутбуке жюри будет 1366×768.
- Скриншоты ключевых экранов в `reports/` (на случай если на демо-показе сеть лагает — будут запасные).
- 1 прогон демо-сценария от начала до конца **с таймером** — должен укладываться в 3 минуты.

## 4. Описания ключевых компонентов

### `useAtRisk` хук

```js
import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export function useAtRisk(params) {
  return useQuery({
    queryKey: ["at-risk", params],
    queryFn: async () => {
      const { data } = await api.get("/clients/at-risk", { params });
      return data;
    },
    staleTime: 30_000,
    keepPreviousData: true, // плавная пагинация без мерцаний
  });
}
```

### Утилита `formatFeatureName`

Маппит технические имена в читаемые (для Top Factors). Список — копия из `model/feature_list.json`:

```js
const NAMES = {
  support_tickets_30d: "Обращения в поддержку (30д)",
  unsubscribe_count_90d: "Отписки от рассылок (90д)",
  days_since_last_login: "Дней без входа в приложение",
  inflow_drop_pct: "Падение поступлений (зарплата)",
  turnover_drop_30d_vs_60d_pct: "Падение оборотов",
  sessions_drop_30d_vs_60d_pct: "Падение активности",
  // ... 39 фич, добавляются по мере обнаружения
};
export const formatFeatureName = (k) => NAMES[k] ?? k;
```

### `ClientsTable` колонки

| Колонка | Источник | Формат |
|---|---|---|
| Имя | `full_name` | text |
| Регион | `geography` | text |
| Скор | `churn_probability_pct` | `${n}%` + цвет градиент |
| Риск | `risk_level` | `<RiskBadge>` |
| Сегмент | `segment` | text |
| Оффер | `offer.title` | text + tooltip с `reason` |
| → | — | `<ChevronRight />` |

## 5. Демо-сценарий (3 минуты, секция 8 исходного плана хакатона)

```
0:00 — открываем дашборд
       «Утро понедельника. Маркетолог СДМ открывает дашборд.
        Видит: 416 клиентов в зоне риска ухода в ближайшие 28 дней.»

0:25 — фильтруем по Москве (145 клиентов)
       «Сегментирует по региону. Видит топ-кандидатов.»

0:45 — кликаем на топового (Дарья Иванова, 99.6%)
       «Открывает карточку. Скор 99.6%, высокий риск.»

1:10 — указываем на TopFactors
       «Система объясняет почему: 2 обращения в поддержку за 30 дней,
        отписалась от рассылок, не заходит в приложение 21 день.»

1:30 — указываем на ActivityChart
       «Вот график активности — три недели назад резкое падение.»

1:50 — указываем на OfferCard
       «Система предлагает: персональный звонок менеджера.
        Маркетолог одним кликом запускает кампанию.»

2:15 — нажимаем CTA → возвращаемся на дашборд
       «Возвращается к списку. Переключает режим на ‘широкий охват’ —
        видит расширенный список для массовой коммуникации.»

2:45 — открываем Swagger /docs
       «Под капотом — REST API на FastAPI. Любая банковская система
        может встроить нашу модель за полчаса.»

3:00 — конец демо.
```

## 6. Параллелизм с другими этапами

```
часы:        8:00   10:00   12:00   14:00   16:00
Антон 4.1-4.9 ███████████████████████████████████  setup → polish
Самир (3.6)    ╔═══ помощь по интеграции (13–14)
Миша           ╔═══ подбор демо-клиентов (14–14:45)
Давид          ╔═══ ревью UI + готовит слайды (Этап 5 параллельно)
```

Антон **не блокируется** ни в одной точке: API живой с часа 8, при простое API есть mock-данные.

## 7. Чек-лист «готово к Этапу 5»

- [ ] `npm run dev` стартует за < 5 сек, `npm run build` без ошибок.
- [ ] `docker compose up --build` поднимает фронт+бэк, фронт открывается на http://localhost:3000.
- [ ] Дашборд показывает 416 клиентов в balanced, 471 в high_recall.
- [ ] Все 4 фильтра работают (geography, segment, min_score, mode).
- [ ] Сортировка по score/имени работает.
- [ ] Карточка клиента показывает score + top_factors + chart + offer.
- [ ] CTA-кнопка на оффере что-то делает (alert или toast — не важно).
- [ ] Loading и error states для каждого API-запроса.
- [ ] Демо-сценарий из секции 5 укладывается в 3 минуты, без падений.
- [ ] 5 скриншотов ключевых экранов в `reports/screenshots/` (страховка).

## 8. Риски и митигации

| Риск | Митигация |
|---|---|
| Tailwind не подхватился, всё некрасиво | Подключить через CDN (`<link href="https://cdn.tailwindcss.com">`) — некрасивое, но рабочее решение для демо |
| Recharts медленный на 90+ точках | Группировать транзакции по дням → ~90 баров max, нормально |
| CORS-ошибки от бэкенда | Уже сконфигурировано на 3000/5173/8080; если ещё что-то — добавить через ENV в `docker-compose.yml` |
| Клик на клиента → 404 (если в `at-risk` есть, а в `/clients/{id}` нет) | На бэкенде `clients_df` единый источник — не должно случиться. Если случилось — Самир чинит за минуту. |
| Демо ломается на live-API | План B: моки в `lib/mock.js` со скриншотами в `reports/screenshots/` |
| Загнали в TypeScript «по-богатому» и не успеваем | Откатиться на JS — просто переименовать `.tsx` → `.jsx`. Решение принять до часа 9:00. |
| Антон зависает в стилях | Hard rule: не более 15 мин на один компонент. Если не уложился — ставит `// TODO: polish` и идёт дальше. |

## 9. После хакатона (backlog, в этап не входит)

- Песочница «What-if»: форма с фичами клиента → live-вызов `/predict`.
- Каталог офферов из `/offers/templates` с фильтрами.
- Аналитика: «Конверсия удержания по офферам» (нужен учёт ответов кампаний на бэке).
- Замена alert на реальный workflow (создание задачи в CRM маркетолога).
