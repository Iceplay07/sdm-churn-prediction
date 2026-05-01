"""
generate_dataset.py — синтетический датасет для прогноза оттока СДМ Банка.

Запуск:
    python generate_dataset.py

Что создаёт:
    data/raw/clients.csv          — статичные профили клиентов (10 000)
    data/raw/transactions.csv     — транзакции по дням
    data/raw/app_sessions.csv     — входы в мобильное приложение
    data/raw/communications.csv   — push, отписки, обращения в поддержку
    data/processed/features.csv   — агрегированный feature-set + таргет
                                    churned_in_next_28d (готов к ML)
    data/raw/_profiles_full.pkl   — служебный кеш состояния (для пересборки)

Логика:
    * 10 000 клиентов, 180 дней истории.
    * ~20% клиентов уйдут (churn_date в днях 60..178).
    * За 28-56 дней до ухода у них постепенно затухает активность —
      это и есть сигнал, который должна ловить модель.
    * Snapshot date = последний день истории - 28 дней.
      Окно наблюдения = последние 90 дней до snapshot.
      Таргет = ушёл ли клиент в следующие 28 дней после snapshot.

Скрипт идемпотентный: если CSV уже на диске, шаг пропускается.
Чтобы перегенерить с нуля — удалите файлы в data/raw/ и data/processed/.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_CLIENTS = 10_000
HISTORY_DAYS = 180
PREDICTION_HORIZON_DAYS = 28
OBSERVATION_WINDOW_DAYS = 90
CHURN_RATE = 0.20

DATA_DIR = Path(__file__).resolve().parent
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

START_DATE = date(2025, 11, 1)
END_DATE = START_DATE + timedelta(days=HISTORY_DAYS - 1)
SNAPSHOT_DATE = END_DATE - timedelta(days=PREDICTION_HORIZON_DAYS)
OBSERVATION_START = SNAPSHOT_DATE - timedelta(days=OBSERVATION_WINDOW_DAYS - 1)

PROFILES_FULL_PATH = RAW_DIR / "_profiles_full.pkl"

rng = np.random.default_rng(SEED)


def generate_profiles(n):
    male_first = ["Ivan", "Aleksandr", "Dmitry", "Sergey", "Maxim", "Andrey",
                  "Alexey", "Mikhail", "Nikita", "Artem", "Pavel", "Kirill"]
    female_first = ["Anna", "Maria", "Elena", "Olga", "Tatiana", "Natalia",
                    "Yulia", "Ekaterina", "Daria", "Irina", "Svetlana", "Ksenia"]
    last_base = ["Ivanov", "Petrov", "Smirnov", "Kuznetsov", "Popov", "Sokolov",
                 "Lebedev", "Kozlov", "Novikov", "Morozov", "Volkov", "Soloviev",
                 "Vasiliev", "Zaitsev", "Pavlov", "Semenov", "Golubev", "Vinogradov",
                 "Bogdanov", "Vorobiev"]

    gender = rng.choice(["M", "F"], n, p=[0.5, 0.5])
    geography = rng.choice(["Moscow", "SaintPetersburg", "Region"], n, p=[0.4, 0.2, 0.4])
    age = np.clip(rng.normal(38, 12, n).round().astype(int), 18, 80)
    tenure_years = rng.integers(0, 11, n)
    credit_score = np.clip(rng.normal(650, 100, n).round().astype(int), 350, 850)
    salary_monthly = np.clip(rng.lognormal(11.0, 0.6, n), 30_000, 1_500_000).round(0)
    has_balance_flag = rng.random(n) > 0.3
    balance = np.where(has_balance_flag, rng.lognormal(11.5, 1.2, n), 0).round(0)
    n_products = rng.choice([1, 2, 3, 4], n, p=[0.5, 0.35, 0.12, 0.03])
    has_credit_card = (rng.random(n) < 0.7).astype(int)
    is_active_member = (rng.random(n) < 0.55).astype(int)

    first_names, last_names = [], []
    for g in gender:
        if g == "M":
            first_names.append(str(rng.choice(male_first)))
            last_names.append(str(rng.choice(last_base)))
        else:
            first_names.append(str(rng.choice(female_first)))
            ln = str(rng.choice(last_base))
            last_names.append(ln + "a")

    return pd.DataFrame({
        "client_id": np.arange(1, n + 1),
        "first_name": first_names,
        "last_name": last_names,
        "gender": gender,
        "age": age,
        "geography": geography,
        "tenure_years": tenure_years,
        "credit_score": credit_score,
        "salary_monthly_rub": salary_monthly.astype(np.int64),
        "balance_rub": balance.astype(np.int64),
        "n_products": n_products,
        "has_credit_card": has_credit_card,
        "is_active_member": is_active_member,
    })


def assign_churn(profiles):
    n = len(profiles)
    z = (
        -0.015 * (profiles["age"].values - 40)
        + 0.6 * (1 - profiles["is_active_member"].values)
        + 0.4 * (profiles["n_products"].values >= 3).astype(int)
        + 0.4 * (profiles["geography"].values == "Region").astype(int)
        + 0.3 * (profiles["tenure_years"].values < 2).astype(int)
        + rng.normal(0, 1, n)
    )
    threshold = np.quantile(z, 1 - CHURN_RATE)
    will_churn = (z > threshold).astype(int)

    churn_day_idx = np.where(
        will_churn == 1,
        rng.integers(60, HISTORY_DAYS, n),
        -1,
    ).astype(int)
    decay_window = np.where(will_churn == 1, rng.integers(28, 57, n), 0).astype(int)

    profiles = profiles.copy()
    profiles["will_churn"] = will_churn
    profiles["churn_day_idx"] = churn_day_idx
    profiles["decay_window_days"] = decay_window
    profiles["churn_date"] = [
        (START_DATE + timedelta(days=int(d))).isoformat() if d >= 0 else ""
        for d in churn_day_idx
    ]
    return profiles


def build_lambda_matrix(profiles, base_lambda):
    n = len(profiles)
    lam = np.broadcast_to(base_lambda[:, None], (n, HISTORY_DAYS)).copy()

    churn_idx = profiles["churn_day_idx"].values
    decay_w = profiles["decay_window_days"].values
    churners = np.where(profiles["will_churn"].values == 1)[0]

    for i in churners:
        cd = int(churn_idx[i])
        dw = int(decay_w[i])
        ds = max(0, cd - dw)
        end = min(cd, HISTORY_DAYS)
        if end > ds:
            t = np.arange(ds, end)
            progress = (t - ds) / max(1, cd - ds)
            lam[i, ds:end] = base_lambda[i] * (1.0 - 0.8 * progress)
        if cd < HISTORY_DAYS:
            lam[i, cd:] = 0.0
    return lam


def generate_transactions(profiles):
    n = len(profiles)
    base = (
        1.0
        + 0.4 * profiles["is_active_member"].values
        + 0.3 * (profiles["salary_monthly_rub"].values > 80_000).astype(int)
    )
    base *= rng.uniform(0.6, 1.4, n)
    lam = build_lambda_matrix(profiles, base)
    n_per_day = rng.poisson(lam).astype(np.int32)
    total = int(n_per_day.sum())
    print(f"  -> transactions total: {total:,}")

    flat_counts = n_per_day.ravel()
    client_ids = np.repeat(profiles["client_id"].values, HISTORY_DAYS)
    day_indices = np.tile(np.arange(HISTORY_DAYS), n)
    tx_client_id = np.repeat(client_ids, flat_counts)
    tx_day_idx = np.repeat(day_indices, flat_counts)

    categories = np.array([
        "grocery", "restaurants", "transport", "entertainment", "utilities",
        "online_shopping", "pharmacy", "transfer_out", "transfer_in", "atm_withdrawal",
    ])
    cat_p = np.array([0.25, 0.10, 0.10, 0.05, 0.08, 0.15, 0.04, 0.10, 0.10, 0.03])
    cat_p /= cat_p.sum()
    cat_idx = rng.choice(len(categories), total, p=cat_p)
    cat_arr = categories[cat_idx]

    cat_mean = np.array([1500, 1800, 350, 2500, 4000, 3000, 1200, 15_000, 0, 5000], dtype=float)
    means = cat_mean[cat_idx]
    salary_by_client = dict(zip(profiles["client_id"].values,
                                profiles["salary_monthly_rub"].values))
    is_in = (cat_arr == "transfer_in")
    sal_for_tx = np.array([salary_by_client[c] for c in tx_client_id[is_in]])
    means[is_in] = sal_for_tx

    amounts = rng.lognormal(np.log(np.maximum(means, 100)) - 0.3, 0.6).round(0).astype(np.int64)
    sign = np.where(is_in, 1, -1)
    signed_amounts = amounts * sign

    dates = [(START_DATE + timedelta(days=int(d))).isoformat() for d in tx_day_idx]

    return pd.DataFrame({
        "client_id": tx_client_id,
        "date": dates,
        "amount_rub": signed_amounts,
        "category": cat_arr,
    })


def generate_app_sessions(profiles):
    n = len(profiles)
    base = 0.6 + 0.7 * profiles["is_active_member"].values
    base *= rng.uniform(0.5, 1.5, n)
    lam = build_lambda_matrix(profiles, base)
    n_per_day = rng.poisson(lam).astype(np.int32)
    total = int(n_per_day.sum())
    print(f"  -> sessions total: {total:,}")

    flat_counts = n_per_day.ravel()
    client_ids = np.repeat(profiles["client_id"].values, HISTORY_DAYS)
    day_indices = np.tile(np.arange(HISTORY_DAYS), n)
    s_client_id = np.repeat(client_ids, flat_counts)
    s_day_idx = np.repeat(day_indices, flat_counts)
    duration_sec = rng.lognormal(4.5, 0.8, total).round(0).astype(np.int32)

    dates = [(START_DATE + timedelta(days=int(d))).isoformat() for d in s_day_idx]
    return pd.DataFrame({
        "client_id": s_client_id,
        "date": dates,
        "duration_sec": duration_sec,
    })


def generate_communications(profiles):
    n = len(profiles)
    cids = profiles["client_id"].values
    will_churn = profiles["will_churn"].values
    churn_day = profiles["churn_day_idx"].values
    decay_w = profiles["decay_window_days"].values
    is_active = profiles["is_active_member"].values

    PUSHES = 50
    push_days = np.sort(rng.choice(HISTORY_DAYS, size=PUSHES, replace=False))

    base_open = 0.35 + 0.2 * is_active
    open_prob = np.broadcast_to(base_open[:, None], (n, PUSHES)).copy()
    received = np.ones((n, PUSHES), dtype=bool)

    for i in np.where(will_churn == 1)[0]:
        cd = int(churn_day[i])
        dw = int(decay_w[i])
        ds = max(0, cd - dw)
        for j, d in enumerate(push_days):
            d = int(d)
            if ds <= d < cd:
                progress = (d - ds) / max(1, cd - ds)
                open_prob[i, j] *= (1 - 0.8 * progress)
            if d >= cd:
                received[i, j] = False

    rand = rng.random((n, PUSHES))
    opened = (rand < open_prob) & received
    sent_only = received & ~opened

    push_day_grid = np.broadcast_to(push_days[None, :], (n, PUSHES))
    cid_grid = np.broadcast_to(cids[:, None], (n, PUSHES))

    parts = []
    if opened.any():
        parts.append(pd.DataFrame({
            "client_id": cid_grid[opened],
            "day_idx": push_day_grid[opened],
            "event": "push_opened",
        }))
    if sent_only.any():
        parts.append(pd.DataFrame({
            "client_id": cid_grid[sent_only],
            "day_idx": push_day_grid[sent_only],
            "event": "push_sent",
        }))

    unsub_rows = []
    churn_idx = np.where(will_churn == 1)[0]
    flags_c = rng.random(len(churn_idx)) < 0.45
    for i, do in zip(churn_idx, flags_c):
        if not do:
            continue
        cd = int(churn_day[i])
        ds = max(0, cd - int(decay_w[i]))
        d = int(rng.integers(ds, max(ds + 1, cd)))
        unsub_rows.append((int(cids[i]), d, "unsubscribe"))
    nonchurn_idx = np.where(will_churn == 0)[0]
    flags_n = rng.random(len(nonchurn_idx)) < 0.05
    for i, do in zip(nonchurn_idx, flags_n):
        if not do:
            continue
        d = int(rng.integers(0, HISTORY_DAYS))
        unsub_rows.append((int(cids[i]), d, "unsubscribe"))
    if unsub_rows:
        parts.append(pd.DataFrame(unsub_rows, columns=["client_id", "day_idx", "event"]))

    ticket_lambda = np.where(will_churn == 1, 1.5, 0.3)
    n_tickets = rng.poisson(ticket_lambda)
    total_tickets = int(n_tickets.sum())
    if total_tickets > 0:
        rep_cid = np.repeat(cids, n_tickets)
        rep_will = np.repeat(will_churn, n_tickets)
        rep_cd = np.repeat(churn_day, n_tickets)
        rep_dw = np.repeat(decay_w, n_tickets)
        ticket_days = np.empty(total_tickets, dtype=np.int32)
        for k in range(total_tickets):
            if rep_will[k] == 1:
                cd = int(rep_cd[k])
                ds = max(0, cd - int(rep_dw[k]))
                ticket_days[k] = int(rng.integers(ds, max(ds + 1, cd)))
            else:
                ticket_days[k] = int(rng.integers(0, HISTORY_DAYS))
        parts.append(pd.DataFrame({
            "client_id": rep_cid,
            "day_idx": ticket_days,
            "event": "support_ticket",
        }))

    df = pd.concat(parts, ignore_index=True)
    df["date"] = [(START_DATE + timedelta(days=int(d))).isoformat() for d in df["day_idx"].values]
    df = df[["client_id", "date", "event"]]
    print(f"  -> communications total: {len(df):,}")
    return df


def build_features(profiles, transactions, sessions, communications):
    snap = SNAPSHOT_DATE
    obs_start = OBSERVATION_START
    win30_start = snap - timedelta(days=30)
    win60_start = snap - timedelta(days=60)

    tx = transactions.copy()
    tx["date_d"] = pd.to_datetime(tx["date"]).dt.date
    s = sessions.copy()
    s["date_d"] = pd.to_datetime(s["date"]).dt.date
    com = communications.copy()
    com["date_d"] = pd.to_datetime(com["date"]).dt.date

    tx_obs = tx[(tx["date_d"] >= obs_start) & (tx["date_d"] <= snap)].copy()
    s_obs = s[(s["date_d"] >= obs_start) & (s["date_d"] <= snap)].copy()
    com_obs = com[(com["date_d"] >= obs_start) & (com["date_d"] <= snap)].copy()

    tx_obs["abs_amount"] = tx_obs["amount_rub"].abs()
    is_outflow = tx_obs["amount_rub"] < 0
    tx_outflow = tx_obs[is_outflow]

    f_tx_count_90 = tx_obs.groupby("client_id").size().rename("tx_count_90d")
    f_tx_outflow_90 = tx_outflow.groupby("client_id")["abs_amount"].sum().rename("turnover_outflow_90d")

    tx_30 = tx_obs[tx_obs["date_d"] >= win30_start]
    tx_outflow_30 = tx_30[tx_30["amount_rub"] < 0]
    f_tx_count_30 = tx_30.groupby("client_id").size().rename("tx_count_30d")
    f_tx_outflow_30 = tx_outflow_30.groupby("client_id")["abs_amount"].sum().rename("turnover_outflow_30d")

    tx_60 = tx_obs[(tx_obs["date_d"] >= win60_start) & (tx_obs["date_d"] < win30_start)]
    tx_outflow_60 = tx_60[tx_60["amount_rub"] < 0]
    f_tx_outflow_60 = tx_outflow_60.groupby("client_id")["abs_amount"].sum().rename("turnover_outflow_60d_prev")

    last_tx = tx[tx["date_d"] <= snap].groupby("client_id")["date_d"].max()
    days_since_last_tx = ((pd.Timestamp(snap) - pd.to_datetime(last_tx)).dt.days
                          .rename("days_since_last_tx"))

    inflow_30 = tx_30[tx_30["category"] == "transfer_in"].groupby("client_id")["abs_amount"].sum().rename("inflow_30d")
    inflow_60_prev = tx_60[tx_60["category"] == "transfer_in"].groupby("client_id")["abs_amount"].sum().rename("inflow_60d_prev")

    f_sess_30 = s_obs[s_obs["date_d"] >= win30_start].groupby("client_id").size().rename("sessions_30d")
    f_sess_60_prev = s_obs[(s_obs["date_d"] >= win60_start) & (s_obs["date_d"] < win30_start)].groupby("client_id").size().rename("sessions_60d_prev")
    last_sess = s[s["date_d"] <= snap].groupby("client_id")["date_d"].max()
    days_since_last_login = ((pd.Timestamp(snap) - pd.to_datetime(last_sess)).dt.days
                             .rename("days_since_last_login"))

    com_30 = com_obs[com_obs["date_d"] >= win30_start]
    f_unsub = com_obs[com_obs["event"] == "unsubscribe"].groupby("client_id").size().rename("unsubscribe_count_90d")
    f_tickets_30 = com_30[com_30["event"] == "support_ticket"].groupby("client_id").size().rename("support_tickets_30d")
    push_sent = com_obs[com_obs["event"].isin(["push_sent", "push_opened"])].groupby("client_id").size().rename("push_received_90d")
    push_opened = com_obs[com_obs["event"] == "push_opened"].groupby("client_id").size().rename("push_opened_90d")

    feats = profiles.set_index("client_id")[[
        "age", "gender", "geography", "tenure_years", "credit_score",
        "salary_monthly_rub", "balance_rub", "n_products",
        "has_credit_card", "is_active_member",
    ]].copy()

    for series in [f_tx_count_90, f_tx_outflow_90, f_tx_count_30, f_tx_outflow_30,
                   f_tx_outflow_60, days_since_last_tx,
                   inflow_30, inflow_60_prev,
                   f_sess_30, f_sess_60_prev, days_since_last_login,
                   f_unsub, f_tickets_30, push_sent, push_opened]:
        feats = feats.join(series, how="left")

    zero_cols = ["tx_count_90d", "tx_count_30d", "turnover_outflow_90d",
                 "turnover_outflow_30d", "turnover_outflow_60d_prev",
                 "inflow_30d", "inflow_60d_prev",
                 "sessions_30d", "sessions_60d_prev",
                 "unsubscribe_count_90d", "support_tickets_30d",
                 "push_received_90d", "push_opened_90d"]
    feats[zero_cols] = feats[zero_cols].fillna(0)
    feats["days_since_last_tx"] = feats["days_since_last_tx"].fillna(999).astype(int)
    feats["days_since_last_login"] = feats["days_since_last_login"].fillna(999).astype(int)

    feats["turnover_drop_30d_vs_60d_pct"] = np.where(
        feats["turnover_outflow_60d_prev"] > 0,
        (feats["turnover_outflow_60d_prev"] - feats["turnover_outflow_30d"]) /
        feats["turnover_outflow_60d_prev"], 0)
    feats["sessions_drop_30d_vs_60d_pct"] = np.where(
        feats["sessions_60d_prev"] > 0,
        (feats["sessions_60d_prev"] - feats["sessions_30d"]) /
        feats["sessions_60d_prev"], 0)
    feats["push_open_rate_90d"] = np.where(
        feats["push_received_90d"] > 0,
        feats["push_opened_90d"] / feats["push_received_90d"], 0)
    feats["inflow_drop_pct"] = np.where(
        feats["inflow_60d_prev"] > 0,
        (feats["inflow_60d_prev"] - feats["inflow_30d"]) / feats["inflow_60d_prev"], 0)

    cd = profiles.set_index("client_id")["churn_day_idx"]
    snap_idx = (snap - START_DATE).days
    churn_in_horizon = ((cd > snap_idx) & (cd <= snap_idx + PREDICTION_HORIZON_DAYS)).astype(int)
    churn_in_horizon.name = "churned_in_next_28d"
    feats = feats.join(churn_in_horizon)

    already = ((cd >= 0) & (cd <= snap_idx)).astype(int)
    already.name = "already_churned_at_snapshot"
    feats = feats.join(already)

    return feats.reset_index()


def get_or_make_profiles():
    if PROFILES_FULL_PATH.exists():
        return pd.read_pickle(PROFILES_FULL_PATH)
    clients_csv = RAW_DIR / "clients.csv"
    if clients_csv.exists():
        df = pd.read_csv(clients_csv)
        df["churn_day_idx"] = np.where(
            df["churn_date"].fillna("") != "",
            (pd.to_datetime(df["churn_date"]) - pd.Timestamp(START_DATE)).dt.days,
            -1,
        ).astype(int)
        df["decay_window_days"] = np.where(
            df["will_churn"] == 1,
            rng.integers(28, 57, len(df)),
            0,
        ).astype(int)
        df.to_pickle(PROFILES_FULL_PATH)
        return df
    profiles = generate_profiles(N_CLIENTS)
    profiles = assign_churn(profiles)
    profiles.to_pickle(PROFILES_FULL_PATH)
    profiles.drop(columns=["churn_day_idx", "decay_window_days"]).to_csv(
        RAW_DIR / "clients.csv", index=False, encoding="utf-8")
    return profiles


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print("[1/5] Profiles")
    profiles = get_or_make_profiles()
    print(f"  ok: {len(profiles):,} clients, churn_rate = {profiles['will_churn'].mean():.1%}")

    tx_path = RAW_DIR / "transactions.csv"
    if tx_path.exists():
        print("[2/5] Transactions: cached, reading...")
        tx = pd.read_csv(tx_path)
        print(f"  ok: {len(tx):,} rows")
    else:
        print("[2/5] Transactions...")
        tx = generate_transactions(profiles)
        tx.to_csv(tx_path, index=False, encoding="utf-8")

    sess_path = RAW_DIR / "app_sessions.csv"
    if sess_path.exists():
        print("[3/5] Sessions: cached, reading...")
        sessions = pd.read_csv(sess_path)
        print(f"  ok: {len(sessions):,} rows")
    else:
        print("[3/5] Sessions...")
        sessions = generate_app_sessions(profiles)
        sessions.to_csv(sess_path, index=False, encoding="utf-8")

    com_path = RAW_DIR / "communications.csv"
    if com_path.exists():
        print("[4/5] Communications: cached, reading...")
        comms = pd.read_csv(com_path)
        print(f"  ok: {len(comms):,} rows")
    else:
        print("[4/5] Communications...")
        comms = generate_communications(profiles)
        comms.to_csv(com_path, index=False, encoding="utf-8")

    print(f"[5/5] features.csv (snapshot = {SNAPSHOT_DATE.isoformat()})...")
    feats = build_features(profiles, tx, sessions, comms)
    feats.to_csv(PROCESSED_DIR / "features.csv", index=False, encoding="utf-8")

    print()
    print("Done.")
    print(f"  clients.csv:        {len(profiles):,}")
    print(f"  transactions.csv:   {len(tx):,}")
    print(f"  app_sessions.csv:   {len(sessions):,}")
    print(f"  communications.csv: {len(comms):,}")
    print(f"  features.csv:       {len(feats):,} | "
          f"churn={feats['churned_in_next_28d'].sum():,} "
          f"({feats['churned_in_next_28d'].mean():.1%}) | "
          f"already_churned={feats['already_churned_at_snapshot'].sum():,}")


if __name__ == "__main__":
    main()
