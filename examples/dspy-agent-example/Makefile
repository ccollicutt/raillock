.DEFAULT_GOAL := help

help:
	@echo "RailLock Makefile Commands:"
	@echo ""
	@awk -F ':' ' \
		/^## / {help=substr($$0,4); next} \
		/^[a-zA-Z0-9_.-]+:/ {if (help!="") {printf "  make %-25s %s\n", $$1, help; help=""}}' Makefile | sort

## Install project dependencies using uv
install:
	@echo "Locking dependencies..."
	uv lock
	@echo "Syncing dependencies..."
	uv sync

## Run the MCP server
run-server:
	python  examples/dspy-agent-example/mcp-server/server.py

## Run the DSPy agent
run-dspy-agent:
	python examples/dspy-agent-example/src/agent/main.py

## Run the DSPy agent with RailLock enabled
run-dspy-agent-raillock:
	RAILLOCK_DEBUG=true PYTHONPATH=examples/dspy-agent-example/src RAILLOCK_ENABLE=true python examples/dspy-agent-example/src/agent/main.py

## Compare RailLock config with server tools
run-dspy-agent-raillock-compare:
	raillock compare --config examples/dspy-agent-example/src/agent/raillock_config.yaml --server "stdio:python examples/dspy-agent-example/mcp-server/server.py"

.PHONY: help install run-server run-dspy-agent run-dspy-agent-raillock raillock-compare 