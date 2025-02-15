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

