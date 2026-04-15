.PHONY: help env-base env-dev install check lint format typecheck test clean build smoke-wheel

help:
	@echo "mysorf-base — available commands:"
	@echo ""
	@echo "  Setup"
	@echo "    make env-dev     Create the development Conda environment"
	@echo "    make install     Install mysorf-base with development extras"
	@echo ""
	@echo "  Quality"
	@echo "    make check       Run all checks (lint + typecheck + test)"
	@echo "    make lint        Run Ruff linter"
	@echo "    make format      Auto-fix formatting with Ruff"
	@echo "    make typecheck   Run MyPy"
	@echo "    make test        Run pytest"
	@echo ""
	@echo "  Release"
	@echo "    make build       Build distribution packages"
	@echo "    make smoke-wheel Build a wheel and smoke-import it from an isolated target dir"
	@echo "    make clean       Remove build and cache artifacts"

env-base:
	conda env create -f conda-recipes/base.yaml

env-dev:
	conda env create -f conda-recipes/dev.yaml

install:
	pip install -e ".[dev]"

check: lint typecheck test

lint:
	ruff check .
	ruff format --check .

format:
	ruff check . --fix
	ruff format .

typecheck:
	mypy src/mysorf_base tests

test:
	pytest

build:
	pip install hatch
	hatch build

smoke-wheel:
	rm -rf /tmp/mysorf-base-wheel-target
	python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
	python -m pip install --no-deps --target /tmp/mysorf-base-wheel-target dist/mysorf_base-*.whl
	PYTHONPATH=/tmp/mysorf-base-wheel-target python -c "import mysorf_base; print(mysorf_base.__version__)"

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .ruff_cache .mypy_cache .hypothesis
	rm -rf .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
