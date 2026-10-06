# DataChat — Architecture Guide

## Overview

DataChat is a monorepo containing four main components:

1. **Backend** (`backend/`) — FastAPI application serving the REST/WebSocket API
2. **Frontend** (`frontend/`) — Next.js 15 web application
3. **Edge Agent** (`edge-agent/`) — Optional Docker container that connects to a database in its own environment
4. **Shared Packages** (`packages/`) — Shared types and database connectors

## System Architecture

```
                    ┌──────────────────────┐
                    │     Web Browser      │
                    │   (Next.js Client)   │
                    └──────────┬───────────┘
                               │ HTTP / WebSocket
                    ┌──────────▼───────────┐
                    │   FastAPI Backend     │
                    │                      │
                    │  ┌────────────────┐  │
                    │  │ Agent System   │  │
                    │  │ (Orchestrator, │  │
                    │  │  SQL, Stats,   │  │
                    │  │  ML, Narrator) │  │
                    │  └───────┬────────┘  │
                    │          │           │
                    │  ┌───────▼────────┐  │
                    │  │  LLM Router    │  │
                    │  │ (Local/Cloud)  │  │
                    │  └───────┬────────┘  │
                    └──────────┼───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   Ollama       │ │  PostgreSQL │ │    Redis    │
    │ (Local LLM)    │ │  (App DB)   │ │  (Cache)    │
    └────────────────┘ └─────────────┘ └─────────────┘
```

## Key Design Decisions

### 1. Monolith-First Architecture

We use a single FastAPI application rather than microservices. This is intentional:
- Simpler deployment and debugging for a solo developer
- Shared memory between components (no serialization overhead)
- Easy to extract services later if scaling demands it

### 2. Agent System Design

The AI agent is decomposed into specialized sub-agents, each responsible for one step:

```
User Query → Planning Agent → [Schema Agent → SQL Agent → Stats Agent → ML Agent] → Narrator Agent → Response
```

Each agent is a Python class with a single `run()` method. The Orchestrator decides which agents to invoke and in what order.

### 3. LLM Router Pattern

The LLM Router abstracts away the underlying model provider. Currently routes to local Ollama, but the same interface supports OpenAI, Anthropic, or any provider.

```python
class LLMProvider(ABC):
    async def generate(self, prompt: str, **kwargs) -> str: ...
    async def generate_structured(self, prompt: str, schema: type) -> BaseModel: ...
```

### 4. Database Connection Security

- All target database connections use **read-only** credentials
- Credentials are encrypted at rest using Fernet (AES-128-CBC)
- Every generated SQL query passes through a validation pipeline before execution
- Hard row-limit cap prevents accidental full-table scans

## Directory Structure

See [README.md](../README.md) for the full project structure.

## Data Flow

### Query Execution Flow

1. User types natural language question in chat
2. Frontend sends WebSocket message to backend
3. Orchestrator analyzes intent, activates relevant agents
4. Schema Agent identifies relevant tables/columns
5. SQL Agent generates and validates SQL
6. Query executes against the target database (via connector)
7. Stats Agent analyzes results (if needed)
8. Narrator Agent explains findings in plain English
9. Viz Agent selects appropriate chart type
10. Streaming response sent back to frontend via WebSocket

### ML Pipeline Flow

1. User selects target column in "Target Selector" mode
2. Backend extracts feature matrix from database
3. Feature Engineering pipeline runs (encoding, scaling, imputation)
4. Model Tournament trains 5+ algorithms in parallel
5. Models evaluated on holdout set, ranked by performance
6. SHAP values computed for winning model
7. Model Card generated with metrics, bias audit, limitations
8. Results streamed to frontend with interactive explainability charts
