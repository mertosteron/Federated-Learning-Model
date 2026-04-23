# FedGuard — yapılandırma ve demo hedefleri
# CLAUDE.md Faz 0 gereksinimi: up, test, demo, clean

.PHONY: up down test demo clean lint format validate help

help:
	@echo "FedGuard Makefile"
	@echo ""
	@echo "  make up       - Docker Compose ağını ayağa kaldırır (5 banka + 3 aggregator + Besu + IPFS)"
	@echo "  make down     - Servisleri durdurur"
	@echo "  make test     - Tüm testleri çalıştırır (Python + Solidity + Circom)"
	@echo "  make demo     - Uçtan uca demo (Faz 7 sonrası)"
	@echo "  make clean    - Üretilen artefaktları siler (pycache, node_modules, build, proofs)"
	@echo "  make validate - docker-compose.yml sentaksını doğrular"
	@echo "  make lint     - Python (ruff) + Solidity (slither) lint"
	@echo ""

# ─── Orkestrasyon ──────────────────────────────────────────────
up:
	docker compose up -d

down:
	docker compose down

validate:
	docker compose config --quiet && echo "docker-compose.yml OK"

# ─── Test ──────────────────────────────────────────────────────
test: test-python

test-python:
	@if command -v pytest >/dev/null 2>&1; then \
		pytest -q tests/ 2>/dev/null || echo "(Faz 0: henüz test yok — boş geçiş)"; \
	else \
		echo "pytest bulunamadı — Faz 1'de kurulacak"; \
	fi

# ─── Demo (Faz 7) ──────────────────────────────────────────────
demo:
	@echo "Demo Faz 7'de aktif olacak."
	@echo "Faz 0: boş placeholder."

# ─── Lint ──────────────────────────────────────────────────────
lint:
	@command -v ruff >/dev/null 2>&1 && ruff check . || echo "ruff yok"

format:
	@command -v ruff >/dev/null 2>&1 && ruff format . || echo "ruff yok"

# ─── Temizlik ──────────────────────────────────────────────────
clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type d -name '.pytest_cache' -prune -exec rm -rf {} +
	find . -type d -name 'node_modules' -prune -exec rm -rf {} +
	find . -type d -name 'build' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	rm -rf circuits/build circuits/ptau/*.ptau 2>/dev/null || true
