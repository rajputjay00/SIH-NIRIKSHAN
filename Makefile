.PHONY: dev test build lint

dev:
	docker compose up --build

test:
	docker run --rm nirikshan pytest -q

build:
	docker build -t nirikshan .

lint:
	cd frontend && npm run build
