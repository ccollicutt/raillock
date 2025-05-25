.PHONY: help install test lint clean run-client run-cli venv reinstall integration-test review-example coverage all-tests create-config review-config run-stdio-server review-stdio-example dev-setup list-config-vs-server sse-compare-example run-sse-server test-unit test-integration-no-env test-integration-with-env

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
	uv sync --dev
	uv pip install -e .

venv: ## Create and set up a Python virtual environment
	python -m venv venv
	. venv/bin/activate && uv pip install -e ".[dev]"

reinstall: ## Recreate .venv and reinstall all packages from scratch
	rm -rf .venv
	uv venv .venv --python 3.11
	uv lock
	uv sync --dev
	uv pip install -e .

# Testing and Linting
## Run all tests and show summary
# make test
test: test-unit test-integration-no-env test-integration-with-env
	@echo "======================================"
	@echo "🎯 RailLock Dynamic Test Results"
	@echo "======================================"

## Run unit tests with coverage (these work fine with PYTHONUNBUFFERED=1)
# make test-unit
test-unit:
	@echo "Running unit tests with coverage..."
	@PYTHONUNBUFFERED=1 uv run pytest -s --cov=raillock tests/unit/ --tb=short > .test-unit-results.tmp 2>&1; \
	TEST_EXIT=$$?; \
	cat .test-unit-results.tmp; \
	if [ $$TEST_EXIT -ne 0 ]; then exit $$TEST_EXIT; fi
	@echo "✅ Unit tests completed"

## Run integration tests that DON'T work with PYTHONUNBUFFERED=1 (stdio test)
# make test-integration-no-env  
test-integration-no-env:
	@echo "Running integration tests without PYTHONUNBUFFERED..."
	@uv run pytest -s -v tests/integration/test_protocols.py::test_stdio_integration --tb=short > .test-integration-no-env-results.tmp 2>&1; \
	TEST_EXIT=$$?; \
	cat .test-integration-no-env-results.tmp; \
	if [ $$TEST_EXIT -ne 0 ]; then exit $$TEST_EXIT; fi
	@echo "✅ Stdio integration tests completed"

## Run integration tests that DO work with PYTHONUNBUFFERED=1 (SSE tests)
# make test-integration-with-env
test-integration-with-env:
	@echo "Running integration tests with PYTHONUNBUFFERED..."
	@PYTHONUNBUFFERED=1 uv run pytest -s -v tests/integration/test_protocols.py::test_sse_integration_with_real_server tests/integration/test_protocols.py::test_minimal_debug tests/integration/test_protocols.py::test_tmp_path_only --tb=short > .test-integration-with-env-results.tmp 2>&1; \
	TEST_EXIT=$$?; \
	cat .test-integration-with-env-results.tmp; \
	if [ $$TEST_EXIT -ne 0 ]; then exit $$TEST_EXIT; fi
	@echo "✅ SSE + misc integration tests completed"
	@echo ""
	@echo "📊 Parsing Dynamic Test Results..."
	@echo "======================================"
	@echo ""
	@unit_passed=$$(grep -o "[0-9]\+ passed" .test-unit-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	unit_skipped=$$(grep -o "[0-9]\+ skipped" .test-unit-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	unit_failed=$$(grep -o "[0-9]\+ failed" .test-unit-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	stdio_passed=$$(grep -o "[0-9]\+ passed" .test-integration-no-env-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	stdio_skipped=$$(grep -o "[0-9]\+ skipped" .test-integration-no-env-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	stdio_failed=$$(grep -o "[0-9]\+ failed" .test-integration-no-env-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	sse_passed=$$(grep -o "[0-9]\+ passed" .test-integration-with-env-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	sse_skipped=$$(grep -o "[0-9]\+ skipped" .test-integration-with-env-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	sse_failed=$$(grep -o "[0-9]\+ failed" .test-integration-with-env-results.tmp | head -1 | cut -d' ' -f1 || echo "0"); \
	coverage=$$(grep -o "[0-9]\+%" .test-unit-results.tmp | tail -1 || echo "N/A"); \
	total_passed=$$((unit_passed + stdio_passed + sse_passed)); \
	total_skipped=$$((unit_skipped + stdio_skipped + sse_skipped)); \
	total_failed=$$((unit_failed + stdio_failed + sse_failed)); \
	echo "📈 Dynamic Results Summary:"; \
	echo "--------------------------------------"; \
	echo "✅ Unit Tests:         $${unit_passed:-0} passed, $${unit_skipped:-0} skipped, $${unit_failed:-0} failed"; \
	echo "✅ Stdio Integration:  $${stdio_passed:-0} passed, $${stdio_skipped:-0} skipped, $${stdio_failed:-0} failed"; \
	echo "✅ SSE + Misc Integ:   $${sse_passed:-0} passed, $${sse_skipped:-0} skipped, $${sse_failed:-0} failed"; \
	echo ""; \
	echo "🎯 Total Results:"; \
	echo "--------------------------------------"; \
	echo "  🟢 Total Passed:    $${total_passed:-0} tests"; \
	echo "  🟡 Total Skipped:   $${total_skipped:-0} tests"; \
	echo "  🔴 Total Failed:    $${total_failed:-0} tests"; \
	echo "  📊 Coverage:        $${coverage:-N/A}"; \
	echo ""; \
	if [ $${total_failed:-0} -eq 0 ]; then \
		echo "🎉 All tests passed successfully!"; \
	else \
		echo "❌ $${total_failed:-0} test(s) failed - check logs above"; \
		exit 1; \
	fi; \
	echo "======================================"
	@rm -f .test-unit-results.tmp .test-integration-no-env-results.tmp .test-integration-with-env-results.tmp





