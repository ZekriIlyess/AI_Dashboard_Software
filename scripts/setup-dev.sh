#!/bin/bash
# =============================================================================
# Nexus AI — Development Setup Script
# =============================================================================
# One-command setup for new development environments.
# Usage: bash scripts/setup-dev.sh
# =============================================================================

set -e

echo ""
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     Nexus AI — Development Setup      ║"
echo "  ╚═══════════════════════════════════════╝"
echo ""

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------
echo "🔍 Checking prerequisites..."

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "  ❌ $1 is not installed. Please install it first."
        exit 1
    else
        echo "  ✅ $1 found: $($1 --version 2>&1 | head -1)"
    fi
}

check_command python
check_command node
check_command docker
check_command git

echo ""

# ---------------------------------------------------------------------------
# Environment file
# ---------------------------------------------------------------------------
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "  ✅ .env created. Edit it with your settings."
else
    echo "  ℹ️  .env already exists, skipping."
fi

echo ""

# ---------------------------------------------------------------------------
# Start infrastructure
# ---------------------------------------------------------------------------
echo "🐳 Starting Docker infrastructure..."
docker compose -f docker/docker-compose.yml up -d postgres redis postgres-test-db
echo "  ✅ PostgreSQL (5432), Test DB (5433), and Redis (6379) are running."
echo "  ⏳ Waiting 5 seconds for databases to initialize..."
sleep 5

echo ""

# ---------------------------------------------------------------------------
# Backend setup
# ---------------------------------------------------------------------------
echo "🐍 Setting up Python backend..."
cd backend

if [ ! -d ".venv" ]; then
    python -m venv .venv
    echo "  ✅ Virtual environment created."
fi

# Activate venv (cross-platform)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source .venv/Scripts/activate
else
    source .venv/bin/activate
fi

pip install -e ".[dev]" --quiet
echo "  ✅ Python dependencies installed."

# Run migrations
python -m alembic upgrade head 2>/dev/null || echo "  ⚠️  Migrations skipped (run manually after first migration)."

cd ..
echo ""

# ---------------------------------------------------------------------------
# Frontend setup
# ---------------------------------------------------------------------------
echo "⚛️  Setting up Next.js frontend..."
cd frontend
npm install --silent
echo "  ✅ Node dependencies installed."
cd ..
echo ""

# ---------------------------------------------------------------------------
# Seed test database
# ---------------------------------------------------------------------------
echo "🌱 Seeding test database..."
cd backend
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
python ../scripts/seed-test-db.py 2>/dev/null || echo "  ⚠️  Seeding skipped (will work after asyncpg is installed)."
cd ..
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "  ╔═══════════════════════════════════════════════╗"
echo "  ║          ✅ Setup Complete!                   ║"
echo "  ╠═══════════════════════════════════════════════╣"
echo "  ║                                               ║"
echo "  ║  Start backend:                               ║"
echo "  ║    cd backend && .venv/Scripts/activate        ║"
echo "  ║    uvicorn app.main:app --reload --port 8000   ║"
echo "  ║                                               ║"
echo "  ║  Start frontend:                              ║"
echo "  ║    cd frontend && npm run dev                  ║"
echo "  ║                                               ║"
echo "  ║  URLs:                                        ║"
echo "  ║    Frontend:  http://localhost:3000             ║"
echo "  ║    Backend:   http://localhost:8000             ║"
echo "  ║    API Docs:  http://localhost:8000/docs        ║"
echo "  ║    pgAdmin:   http://localhost:5050 (optional)  ║"
echo "  ║                                               ║"
echo "  ╚═══════════════════════════════════════════════╝"
echo ""
