# How Much

Painel de telemetria com dados fictícios de "quanto está custando" — uma tela
de login e um dashboard em tempo real (KPIs, gráfico de linha, distribuição
por categoria e um feed de leituras) que simula o consumo/custo de fontes
conectadas. Serve como base de estudo/demo de um projeto Django completo:
autenticação, tema claro/escuro, API JSON autenticada e front-end sem
framework (JS puro).

Stack: **Django 5** + **PostgreSQL 16**, com um app único (`core`) responsável
por login, dashboard e a API de telemetria.

## Ideia

- `core/telemetry.py` gera os números fictícios exibidos no painel — não há
  integração com fontes reais, é só para demonstração visual.
- Tudo fica atrás de login (`django.contrib.auth`); existe um comando
  `manage.py bootstrap` idempotente que cria o superusuário a partir das
  variáveis `ADMIN_*` do `.env`.
- `/api/telemetria/` devolve o mesmo snapshot usado no dashboard, em JSON,
  para quem estiver autenticado — pensado para alimentar o polling do
  front-end.

## Rodando com Docker (recomendado)

Pré-requisito: Docker + Docker Compose.

```bash
cp .env.example .env        # ajuste os valores, principalmente as senhas
docker compose up -d --build
```

Isso sobe dois serviços:

- `db` — Postgres 16, exposto em `127.0.0.1:${DB_PORT}` (padrão 5433).
- `web` — Django, exposto em `127.0.0.1:${WEB_PORT}` (padrão 8011). No
  startup ele roda `migrate`, `bootstrap` (cria/atualiza o superusuário) e
  sobe o `runserver`.

Acesso: **http://localhost:8011**

- Painel: `/` (exige login) · Login: `/login/`
- Admin do Django: `/admin/`
- API da telemetria (autenticada): `/api/telemetria/`

Usuário/senha do superusuário: `ADMIN_USER` / `ADMIN_PASSWORD` do `.env`.

## Rodando sem Docker

```bash
docker compose up -d db          # só o Postgres
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py bootstrap
.venv/bin/python manage.py runserver 127.0.0.1:8010
```

## Estrutura

```
config/     settings, urls e wsgi do projeto Django
core/       app único: models, views, forms, telemetria fictícia e templates
static/     css/js/img servidos via staticfiles
Dockerfile, docker-compose.yml    imagem da app + Postgres
```

> ⚠️ Projeto de estudo/demo. `DJANGO_DEBUG=1` e o `runserver` do Django não
> são adequados para produção.
