.PHONY: db api web test

db:
	docker compose up -d db

api:
	cd apps/api && uvicorn app.main:app --reload

web:
	cd apps/web && npm run dev

test:
	cd apps/api && pytest

