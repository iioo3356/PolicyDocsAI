.PHONY: db api web test check-rules check-docs test-docs

db:
	docker compose up -d db

api:
	cd apps/api && uvicorn app.main:app --reload

web:
	cd apps/web && npm run dev

test: check-rules test-docs
	cd apps/api && pytest


check-rules: check-docs
	python3 scripts/check_rules.py

check-docs:
	python3 scripts/check_docs.py

test-docs:
	python3 -m unittest discover -s scripts/tests -p "test_*.py"
