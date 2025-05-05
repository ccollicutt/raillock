.PHONY: help run-server run-client run-server-sse run-client-sse clean test-echo-railpath integration-test reinstall

PYTHON := .venv/bin/python
ifeq (,$(wildcard $(PYTHON)))
PYTHON := python
endif

help:
	@echo "Available commands:"
	@echo "  make help         Show this help message."
	@echo "  make run-server   Run the echo MCP server."
	@echo "  make run-client   Run the echo MCP client (launches server as subprocess)."
	@echo "  make run-server-sse Run the SSE echo server."
	@echo "  make run-client-sse Run the SSE echo client."
	@echo "  make clean        Remove __pycache__ and .pyc files."
	@echo "  make test-echo-railpath Run the echo server and RailLock-enabled client using local .venv."
	@echo "  make integration-test Run the echo server and echo_client_railpath.py using the local .venv, checks for expected output, and prints the server log if the test fails."
	@echo "  make reinstall    Recreate .venv and reinstall dependencies."

install:
	uv venv .venv --python 3.11
	uv sync

run-server:
	$(PYTHON) echo_server.py

run-client:
	$(PYTHON) echo_client.py

run-server-sse:
	$(PYTHON) echo_server_sse.py

run-client-sse:
	$(PYTHON) echo_client_sse.py

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

test-echo-railpath:
	@echo "Starting echo server and RailLock-enabled client using local .venv..."
	. .venv/bin/activate && PYTHONUNBUFFERED=1 python echo_server.py > echo_server.log 2>&1 & \
	SERVER_PID=$$!; \
	sleep 3; \
	. .venv/bin/activate && python echo_client_railpath.py || (echo "\n--- ECHO SERVER LOG ---" && cat echo_server.log); \
	kill $$SERVER_PID 

integration-test:
	@echo "Running integration test: echo server + RailLock client..."
	. .venv/bin/activate && PYTHONUNBUFFERED=1 python echo_server.py > echo_server.log 2>&1 & \
	SERVER_PID=$$!; \
	sleep 3; \
	OUTPUT=`. .venv/bin/activate && ./echo_client_railpath.py 2>&1`; \
	RET=$$?; \
	echo "$$OUTPUT" | tee integration_test_output.log; \
	if echo "$$OUTPUT" | grep -q 'allowed by RailLock: True' && echo "$$OUTPUT" | grep -q 'allowed by RailLock: False'; then \
		echo "Integration test PASSED"; \
	else \
		echo "Integration test FAILED"; \
		echo "\n--- ECHO SERVER LOG ---"; \
		cat echo_server.log; \
		false; \
	fi; \
	kill $$SERVER_PID 

reinstall: ## Recreate .venv and reinstall dependencies using uv
	rm -rf .venv
	uv venv .venv --python 3.11 # Or your desired Python version
	. .venv/bin/activate && uv sync