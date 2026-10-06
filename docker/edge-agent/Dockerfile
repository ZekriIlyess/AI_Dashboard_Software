# =============================================================================
# Nexus AI - Edge Agent Dockerfile
# =============================================================================
# Hardened container for deployment inside customer's network.
# Connects to customer DB (read-only) and tunnels to Nexus Cloud.
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy edge agent code
COPY edge-agent/ ./edge-agent/
COPY packages/shared-types/python/ ./packages/shared-types/python/
COPY packages/db-connectors/ ./packages/db-connectors/

# Install dependencies
RUN pip install --no-cache-dir ./edge-agent ./packages/db-connectors

# Create non-root user (security: never run as root)
RUN groupadd -r nexus-agent && useradd -r -g nexus-agent nexus-agent

# Create directories for ephemeral data (no persistent storage)
RUN mkdir -p /tmp/nexus-agent && chown nexus-agent:nexus-agent /tmp/nexus-agent

USER nexus-agent

# Environment
ENV PYTHONUNBUFFERED=1
ENV AGENT_TEMP_DIR=/tmp/nexus-agent

EXPOSE 8443

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8443/health || exit 1

CMD ["uvicorn", "edge-agent.agent.main:app", "--host", "0.0.0.0", "--port", "8443"]
