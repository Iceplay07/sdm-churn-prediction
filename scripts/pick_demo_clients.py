"""
Подбирает 6 'живых' клиентов для демо: по одному на каждый ключевой тип оффера + один loyal.

Использует precompute_scores из бэкенда, чтобы получить уже посчитанные скоры + офферы.
Сохраняет результат в frontend/public/demo_clients.json.

Запуск (из корня проекта):
    python -m scripts.pick_demo_clients
"""
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.data_loader import precompute_scores

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "demo_clients.json"

TARGET_OFFERS = [
    "manager_call",
    "comm_resettings",
    "salary_bonus",
    "cashback_grocery_5pct",
    "app_reactivation_gift",
]


def main():
    print("[demo] precomputing scores...")
    df = precompute_scores(mode="balanced")
    print(f"[demo] dataframe: {len(df)} rows")

    # Распакуем offer_id для удобства фильтрации
    df["offer_id"] = df["offer"].apply(lambda o: o.get("id") if isinstance(o, dict) else None)

    picks = []

    for offer_id in TARGET_OFFERS:
        sub = df[(df["offer_id"] == offer_id) & (df["is_at_risk"] == True)].copy()
        if sub.empty:
            print(f"[demo] WARN: no at-risk client with offer={offer_id}")
            continue
        # Берём с самым высоким скором — самый яркий кейс
        best = sub.sort_values("churn_score", ascending=False).iloc[0]
        picks.append(best)
        print(f"  + {offer_id:<30} client_id={best['client_id']} score={best['churn_score']:.3f}"
              f"  ({best['full_name']})")

    # Один лояльный для контраста
    loyal = df[df["is_at_risk"] == False].sort_values("churn_score").iloc[0]
    picks.append(loyal)
    print(f"  + {'LOYAL':<30} client_id={loyal['client_id']} score={loyal['churn_score']:.3f}"
          f"  ({loyal['full_name']})")

    out = {
        "generated_from": "backend.data_loader.precompute_scores(balanced)",
        "n_picks": len(picks),
        "client_ids": [int(p["client_id"]) for p in picks],
        "items": [
            {
                "client_id": int(p["client_id"]),
                "full_name": p["full_name"],
                "geography": p["geography"],
                "segment": p["segment"],
                "churn_score": float(p["churn_score"]),
                "risk_level": p["risk_level"],
                "is_at_risk": bool(p["is_at_risk"]),
                "offer_id": p["offer_id"],
                "offer_title": p["offer"].get("title") if isinstance(p["offer"], dict) else None,
                "demo_role": (
                    "loyal" if not p["is_at_risk"]
                    else f"offer:{p['offer_id']}"
                ),
            }
            for p in picks
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\n[demo] saved {len(picks)} clients to {OUT}")


if __name__ == "__main__":
    main()
