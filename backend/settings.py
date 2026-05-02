"""Конфиг бэкенда. Берём из ENV, дефолты подходят для локальной разработки и docker-compose."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# CORS — фронт Антона (vite dev = 5173, CRA = 3000), плюс docker-compose host
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8080",
    ).split(",")
    if o.strip()
]

# Пути к данным — можно переопределить через ENV в docker-compose
FEATURES_CSV = Path(os.getenv("FEATURES_CSV", str(ROOT / "data" / "processed" / "features.csv")))
CLIENTS_CSV = Path(os.getenv("CLIENTS_CSV", str(ROOT / "data" / "raw" / "clients.csv")))
TRANSACTIONS_CSV = Path(os.getenv("TRANSACTIONS_CSV", str(ROOT / "data" / "raw" / "transactions.csv")))

# Лимиты API
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "1000"))
MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", "500"))
DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
