.PHONY: help install test lint clean run-client run-cli venv reinstall integration-test review-example coverage all-tests create-config review-config run-stdio-server review-stdio-example dev-setup list-config-vs-server sse-compare-example run-sse-server

# Default target
.DEFAULT_GOAL := help

# Dynamically generate help from comments beginning with ##
help: ## Display this help message
	@echo "RailLock Makefile Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-20s %s\n", $$1, $$2}' | sort

# Development setup
install: ## Install the package in development mode and set up .venv if needed
	@if [ ! -d ".venv" ]; then \
		echo "Creating .venv with uv..."; \
		uv venv .venv --python 3.11; \
	fi
	. .venv/bin/activate && uv pip install -e ".[dev]"


venv: ## Create and set up a Python virtual environment
	python -m venv venv
	. venv/bin/activate && uv pip install -e ".[dev]"

reinstall: ## Recreate .venv and reinstall all packages from scratch
	rm -rf .venv
	uv venv .venv --python 3.11
	. .venv/bin/activate && uv pip install -e ".[dev]"

# Testing and Linting
test: ## Run all tests and show summary
	@echo "------------------------------------"
	@echo "\033[1;34mRunning tests...\033[0m\033[3mthis may take a while to show output\033[0m"
	PYTHONUNBUFFERED=1 pytest -s --cov=raillock tests
	@echo "------------------------------------"





