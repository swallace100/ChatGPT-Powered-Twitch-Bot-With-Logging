# -------- Chat Bot Makefile (Windows + POSIX Compatible) --------

ifeq ($(OS),Windows_NT)
  VENV_BIN := .venv\Scripts
  PY := $(VENV_BIN)\python.exe
  PIP := $(VENV_BIN)\pip.exe
  PY_CREATE := py -3.13
else
  VENV_BIN := .venv/bin
  PY := $(VENV_BIN)/python
  PIP := $(VENV_BIN)/pip
  PY_CREATE := python3
endif

ENV_FILE ?= resources/appSettings.env

.PHONY: help venv install install-dev run tokens freeze clean show-env ensure-env lint format precommit

help:
	@echo "Targets:"
	@echo "  make venv         - Create .venv (Python 3.13+)"
	@echo "  make install      - Install runtime deps into .venv"
	@echo "  make install-dev  - Install dev deps + pre-commit hook"
	@echo "  make run          - Run the bot (uses $(ENV_FILE))"
	@echo "  make tokens       - Launch Twitch device flow to populate tokens"
	@echo "  make freeze       - Export exact versions to requirements.lock.txt"
	@echo "  make clean        - Remove caches and .venv"
	@echo "  make show-env     - Print resolved env file path"
	@echo "  make lint/format  - Ruff and Black"
	@echo "  make precommit    - Run all pre-commit hooks on repo"
	@echo ""
	@echo "Tip: Copy resources/appSettings.env_example to $(ENV_FILE) and edit."

# ---- Environment setup ----

venv:
	$(PY_CREATE) -m venv .venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# Cross-platform install-dev (handles Windows and POSIX)
ifeq ($(OS),Windows_NT)
install-dev: install
	@echo Installing development dependencies...
	@if exist requirements-dev.txt ( \
		$(PIP) install -r requirements-dev.txt \
	) else ( \
		echo "No requirements-dev.txt found, skipping." \
	)
	@echo Installing pre-commit hook...
	$(PY) -m pre_commit install
else
install-dev: install
	@echo "Installing development dependencies..."
	@if [ -f requirements-dev.txt ]; then $(PIP) install -r requirements-dev.txt; else echo "No requirements-dev.txt found, skipping."; fi
	@echo "Installing pre-commit hook..."
	$(PY) -m pre_commit install
endif

# ---- Core actions ----

run: ensure-env
	$(PY) main.py

tokens: ensure-env
	$(PY) get_tokens.py

freeze:
	$(PIP) freeze > requirements.lock.txt
	@echo "Wrote requirements.lock.txt"

show-env:
	@echo $(ENV_FILE)

# ---- Helpers ----

ifeq ($(OS),Windows_NT)
ensure-env:
	@if not exist "$(ENV_FILE)" ( \
		if not exist "resources" mkdir resources & \
		copy /Y "resources\\appSettings.env_example" "$(ENV_FILE)" >NUL & \
		echo Created $(ENV_FILE) from template. Please review & edit it. \
	)
else
ensure-env:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		mkdir -p resources && \
		cp resources/appSettings.env_example "$(ENV_FILE)" && \
		echo "Created $(ENV_FILE) from template. Please review & edit it."; \
	fi
endif

clean:
	@echo Cleaning...
ifeq ($(OS),Windows_NT)
	-@if exist .venv rmdir /S /Q .venv
	-@if exist __pycache__ rmdir /S /Q __pycache__
	-@if exist logs rmdir /S /Q logs
	-@if exist requirements.lock.txt del /F /Q requirements.lock.txt
else
	-rm -rf .venv __pycache__ logs
	-rm -f requirements.lock.txt
endif

# ---- QA / tooling ----

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m black .

precommit:
	$(PY) -m pre_commit run --all-files
