<div align="center">

# 📊 DataChat

### Ask your database questions in plain English

*Connect a database, ask a question, get validated SQL, a chart, and a plain-English answer.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)

</div>

---

## About this project

DataChat is a full-stack analytics app I built to learn how to combine LLMs with a
real data stack end-to-end. You connect a database, ask a question in natural language,
and a set of cooperating AI agents turn it into validated SQL, run it, and explain the
result with an appropriate chart.

> This is a personal learning project, not a commercial product. I built it solo to
> practice agent orchestration, SQL generation, FastAPI, and Next.js. Some parts are
> more finished than others (see [Project status](#project-status) below).

## What it does

- 🗣️ **Ask questions in natural language** — "What were total sales last quarter?"
- 🤖 **AI-generated SQL** — generated, validated, and explained before it runs
- 📊 **Interactive dashboards** — charts auto-selected from the query results
- 🔍 **Schema-aware agents** — the system reads your schema and reasons over it
- 🏠 **Local LLM inference** — runs against Ollama by default, so data stays on your machine

## Architecture

DataChat is a monorepo with a FastAPI backend, a Next.js frontend, and an optional
edge agent for connecting to a database in its own environment.

```
┌──────────────────────┐
│     Web Browser      │
│   (Next.js Client)   │
└──────────┬───────────┘
           │ HTTP / WebSocket
┌──────────▼───────────┐
│   FastAPI Backend    │
│  ┌────────────────┐  │
│  │ Agent System   │  │   Schema → SQL → Stats → (ML) → Narrator
│  │  + LLM Router  │  │
│  └───────┬────────┘  │
└──────────┼───────────┘
   ┌───────┼───────┐
┌──▼───┐ ┌─▼────┐ ┌▼─────┐
│Ollama│ │Postgre│ │Redis │
│(LLM) │ │  SQL  │ │Cache │
└──────┘ └───────┘ └──────┘
```

See [`docs/architecture.md`](docs/architecture.md) for details.

## Project status

| Area | Status |
|------|--------|
| Natural-language → SQL → results | ✅ Working |
| Auto-generated dashboards & charts | ✅ Working |
| Schema analysis & agent orchestration | ✅ Working |
| Local LLM inference (Ollama) | ✅ Working |
| ML pipeline (AutoML / predictions / SHAP) | 🧪 Experimental — built but not thoroughly tested |

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy 2.0, Celery |
| Frontend | Next.js 15, D3.js, Recharts, Zustand |
| AI/ML | Ollama (local LLM), XGBoost, SHAP, Prophet |
| Database | PostgreSQL, Redis |
| Infrastructure | Docker Compose |

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- [Ollama](https://ollama.com) (for local LLM inference)

### Development setup

```bash
# Copy environment variables and fill in your own values
cp .env.example .env

# Start infrastructure (PostgreSQL, Redis, Ollama)
docker compose -f docker/docker-compose.yml up -d

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Or use the Makefile: `make dev`, `make test`, `make lint`, `make build`.

> **Note:** Never commit your `.env` file — it holds secrets and is already gitignored.
> Use `.env.example` as the template.

## Project structure

```
datachat/
├── backend/     # FastAPI application (agents, API, ML)
├── frontend/    # Next.js web application
├── edge-agent/  # Optional standalone edge agent (Docker)
├── packages/    # Shared types & database connectors
├── docker/      # Docker configurations
├── scripts/     # Dev & deployment scripts
└── docs/        # Documentation
```

## Supported databases

| Database | Status |
|----------|--------|
| PostgreSQL | ✅ Supported |
| MySQL | ✅ Supported |
| SQLite | 🚧 In progress |


---

<div align="center">
  <strong>A learning project by Ilyes Zekri</strong>
</div>
