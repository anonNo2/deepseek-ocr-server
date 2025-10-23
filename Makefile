# Makefile for DeepSeek OCR Server

.PHONY: help setup install start start-dev stop test clean docker-build docker-up docker-down docker-logs

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)DeepSeek OCR Server - Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

setup: ## Run initial setup (copy modules and create .env)
	@echo "$(BLUE)Running setup...$(NC)"
	@bash setup.sh

install: ## Install Python dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@pip3 install -r requirements.txt

start: ## Start the server
	@echo "$(BLUE)Starting server...$(NC)"
	@bash start_server.sh

start-dev: ## Start server in development mode with auto-reload
	@echo "$(BLUE)Starting server in development mode...$(NC)"
	@uvicorn app:app --host 0.0.0.0 --port 8000 --reload

stop: ## Stop the server
	@echo "$(YELLOW)Stopping server...$(NC)"
	@pkill -f "python3 app.py" || pkill -f "uvicorn app:app" || echo "No server running"

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	@python3 test_server.py

test-api: ## Test API with sample PDF
	@echo "$(BLUE)Testing API...$(NC)"
	@python3 api_client.py ../demo_input/成人糖尿病食养指南\(2023年版\).pdf

clean: ## Clean temporary files and outputs
	@echo "$(YELLOW)Cleaning up...$(NC)"
	@rm -rf temp/
	@rm -rf test_output/
	@rm -rf output/
	@rm -rf __pycache__/
	@rm -rf .pytest_cache/
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@echo "$(GREEN)Cleanup complete$(NC)"

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	@docker-compose build

docker-up: ## Start service with Docker Compose
	@echo "$(BLUE)Starting service with Docker...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)Service started. View logs with 'make docker-logs'$(NC)"

docker-down: ## Stop Docker Compose services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	@docker-compose down

docker-logs: ## View Docker logs
	@docker-compose logs -f

docker-clean: ## Clean Docker resources
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	@docker-compose down -v
	@docker system prune -f

env: ## Create .env from .env.example
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Creating .env file...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN).env file created. Please edit it with your settings.$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists$(NC)"; \
	fi

check: ## Check if all requirements are met
	@echo "$(BLUE)Checking requirements...$(NC)"
	@echo -n "Python 3: "
	@which python3 > /dev/null && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "pip3: "
	@which pip3 > /dev/null && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "CUDA: "
	@which nvidia-smi > /dev/null && echo "$(GREEN)✓$(NC)" || echo "$(YELLOW)⚠ (optional)$(NC)"
	@echo -n ".env file: "
	@[ -f .env ] && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "deepseek_ocr.py: "
	@[ -f deepseek_ocr.py ] && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗ (run 'make setup')$(NC)"

health: ## Check if server is running
	@echo "$(BLUE)Checking server health...$(NC)"
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "$(RED)Server not responding$(NC)"

# Quick start for new users
quickstart: setup install start ## Quick start: setup, install, and start server

# Full setup and start for new users
all: setup install test start ## Complete setup: setup, install, test, and start
