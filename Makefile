# Football Predictor Makefile
# Usage: make <target>

.PHONY: dev test lint build train logs clean install help

BACKEND_DIR := backend
FRONTEND_DIR := frontend
PYTHON := python
PIP := pip

##@ Development

dev-backend: ## Start FastAPI dev server with hot-reload
	cd $(BACKEND_DIR) && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start Vite dev server
	cd $(FRONTEND_DIR) && npm run dev

dev: ## Start both backend + frontend in parallel
	@echo "Starting backend and frontend..."
	@make -j2 dev-backend dev-frontend

##@ Testing

test-backend: ## Run all backend pytest tests
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest tests/ -v --tb=short

test-frontend: ## Run Vitest frontend tests
	cd $(FRONTEND_DIR) && npx vitest run

test: test-backend test-frontend ## Run full test suite

##@ Code Quality

lint-backend: ## Ruff lint on backend
	cd $(BACKEND_DIR) && $(PYTHON) -m ruff check . --fix 2>/dev/null || echo "ruff not installed, skipping"

lint-frontend: ## ESLint on frontend
	cd $(FRONTEND_DIR) && npm run lint

lint: lint-backend lint-frontend ## Lint both backend and frontend

##@ Model Management

train: ## Trigger a competition training (PL by default)
	curl -s -X POST http://localhost:8000/api/train/competition/PL | python -m json.tool

model-status: ## Check model training status
	curl -s http://localhost:8000/api/model/status | python -m json.tool

model-metrics: ## Show backtesting metrics
	curl -s http://localhost:8000/api/model/metrics | python -m json.tool

model-reset: ## Delete cached model and reset to heuristic
	curl -s -X DELETE http://localhost:8000/api/model/cache | python -m json.tool

##@ Infrastructure

install-backend: ## Install backend Python dependencies
	cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt

install-frontend: ## Install frontend npm dependencies
	cd $(FRONTEND_DIR) && npm install

install: install-backend install-frontend ## Install all dependencies

build: ## Build Docker images
	docker-compose build

up: ## Start Docker services
	docker-compose up -d

down: ## Stop Docker services
	docker-compose down

##@ Logs & Monitoring

logs: ## Tail backend Docker logs
	docker-compose logs -f backend

logs-backend: ## Show local backend app logs
	tail -f $(BACKEND_DIR)/logs/app.log 2>/dev/null || echo "No log file yet"

health: ## Check API health endpoint
	curl -s http://localhost:8000/health | python -m json.tool

##@ Cleanup

clean: ## Remove compiled Python files, log, db, model cache
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null; true
	rm -rf $(BACKEND_DIR)/data/ $(BACKEND_DIR)/model_cache/ $(BACKEND_DIR)/logs/
	@echo "Cleaned caches, data, and logs"

##@ Help

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help
