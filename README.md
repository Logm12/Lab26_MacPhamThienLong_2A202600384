# Database Model Context Protocol (MCP) Server

This repository provides a production-grade MCP server built with **FastMCP** exposing powerful, safe SQL capabilities for both **SQLite** and **PostgreSQL** databases.

---

## Key Features & Architecture

1. **Dual-Backend Engine**: Unified interface allowing hot-swappable support for SQLite or PostgreSQL via environment variables.
2. **Poka-Yoke (Fail-Safe) Security**:
   - **Strict Schema Validation**: All user inputs (table and column names) are validated against real runtime catalog definitions before being interpolated.
   - **Query Parameterization**: All values are parameterized (`?` or `%s`) guarding completely against SQL injection.
3. **Strong System Boundaries**: FastMCP tool definitions wrapped in robust type-checked Pydantic schemas.
4. **Static Analysis Compliant**: Fully typed, compliant with `mypy`, and styled using `ruff`.

---

## Quickstart Guide

### 1. Spin up Prerequisites

Ensure your environment has Python 3.10+ and Docker running.

```bash
# 1. Start PostgreSQL Backend
docker run -d --name mcp-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=mcp_lab -p 5432:5432 postgres:latest

# 2. Install Python Dependencies
pip install fastmcp pydantic psycopg2-binary pytest ruff mypy
```

### 2. Database Seeding

Execute the initialization utility to bootstrap schemas and insert initial seed data (`students`, `courses`, `enrollments`) into both SQLite and PostgreSQL:

```bash
python init_db.py
```

---

## Testing & Repeatable Verification

We enforce two levels of automated testing:

### 1. Programmatic Lifecycle Verification

Run the live integration tests against the active databases to verify tables, searches, inserts, aggregates, and injection rejection.

```bash
python verify_server.py
```

### 2. Automated Unit Tests (Pytest)

Run our comprehensive suite to assert adapter boundaries and error conditions.

```bash
python -m pytest tests/
```

---

## Client Configuration (Claude Desktop & Antigravity)

### A. Claude Desktop Integration

Configure your local server within the `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac):

```json
{
  "mcpServers": {
    "sqlite-lab": {
      "command": "python",
      "args": [
        "e:/VinAI/assignments/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"
      ],
      "env": {
        "DATABASE_TYPE": "sqlite",
        "DATABASE_PATH": "e:/VinAI/assignments/Day26-Track3-MCP-tool-integration/implementation/lab.db"
      }
    },
    "postgres-lab": {
      "command": "python",
      "args": [
        "e:/VinAI/assignments/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py"
      ],
      "env": {
        "DATABASE_TYPE": "postgres",
        "DATABASE_URI": "postgresql://postgres:postgres@localhost:5432/mcp_lab"
      }
    }
  }
}
```

### B. Antigravity Config

Create an `mcp_config.json` in your local directory pointing directly to the Python runtime as shown above.

### C. MCP Inspector (Local Debugging)

Run with standard Inspector console:

```bash
npx @modelcontextprotocol/inspector python mcp_server.py
```

---

## 📡 Transport Modes (Bonus)

By default, the server launches on **stdio** for local IPC. Thanks to FastMCP, running as an HTTP SSE stream is natively supported out-of-the-box by appending the command flag:

```bash
python mcp_server.py --transport sse
```
