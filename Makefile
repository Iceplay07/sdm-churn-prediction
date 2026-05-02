.PHONY: install run test lint docker-build docker-up

install:
	pip install -r backend/requirements.txt

run:
	uvicorn backend.main:app --reload --port 8000

test:
	# basetemp в /tmp — чтобы pytest не падал на Cyrillic-пути
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B -m pytest backend/tests -v --basetemp=/tmp/pytest_basetemp

train:
	python -m model.train

docker-build:
	docker compose build

docker-up:
	docker compose up
