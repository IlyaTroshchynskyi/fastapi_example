migration:
	alembic revision --autogenerate -m "$(MSG)"

migrate:
	alembic upgrade head

upgrade:
	alembic upgrade +1

downgrade:
	alembic downgrade -1

lint:
	ruff format
	ruff check --fix

lint-no-format:
	ruff check
	mypy --follow-imports=skip

typecheck:
	mypy --follow-imports=skip

typecheck-report:
	mypy --follow-imports=skip --html-report mypy-report

typecheck-cache-clear:
	rm -rf .mypy_cache

typecheck-your-code-only:
	mypy app --follow-imports=skip --ignore-missing-imports

test:
	coverage run -m pytest
	coverage report

test-no-coverage:
	pytest

test-html:
	coverage run -m pytest
	coverage html

run_app:
	uvicorn app.main:app --reload --port=8005

