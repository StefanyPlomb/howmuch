.DEFAULT_GOAL := help
.PHONY: help env up down restart logs ps build clean

help: ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-10s %s\n", $$1, $$2}'

env: ## Cria o .env a partir do .env.example (se ainda não existir)
	@if [ ! -f .env ]; then cp .env.example .env && echo ">> .env criado a partir do .env.example (ajuste as senhas)"; fi

up: env ## Builda a imagem e sobe o projeto (db + web)
	docker compose up -d --build
	@echo ">> Pronto: http://localhost:$${WEB_PORT:-8011}"

down: ## Derruba os containers
	docker compose down

restart: down up ## Reinicia o projeto

build: env ## Só builda a imagem
	docker compose build

logs: ## Acompanha os logs
	docker compose logs -f

ps: ## Status dos containers
	docker compose ps

clean: ## Derruba tudo e apaga o volume do banco (DESTRUTIVO)
	docker compose down -v
