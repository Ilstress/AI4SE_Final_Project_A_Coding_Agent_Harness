.PHONY: test lint typecheck install clean

install:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check harness/ tests/

typecheck:
	mypy harness/ tests/

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +