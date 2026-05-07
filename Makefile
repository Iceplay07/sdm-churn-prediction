.PHONY: install run frontend test demo train docker-build docker-up

install:
	pip install -r backend/requirements.txt

run:
	uvicorn backend.main:app --reload --port 8000

frontend:
	# Простой статический сервер (CDN-стратегия — npm install не нужен)
	cd frontend && python3 -m http.server 5173

test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B -m pytest backend/tests -v --basetemp=/tmp/pytest_basetemp

demo:
	python -m scripts.pick_demo_clients

train:
	python -m model.train

docker-build:
	docker compose build

docker-up:
	docker compose up
