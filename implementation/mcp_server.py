import json
import os
import sys
from typing import Any, Dict, List, Optional
try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated
from pydantic import BaseModel, Field
from fastmcp import FastMCP

from db import SQLiteAdapter, PostgresAdapter, BaseDatabaseAdapter, ValidationError

# Initialize FastMCP server using the standard naming convention
mcp = FastMCP("database_mcp")

# Determine backend adapter based on environment variables
DB_TYPE = os.environ.get("DATABASE_TYPE", "sqlite").lower()
DB_PATH = os.environ.get("DATABASE_PATH", "lab.db")
DB_URI = os.environ.get("DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/mcp_lab")

adapter: BaseDatabaseAdapter

if DB_TYPE == "postgres":
    try:
        print("Starting MCP server with PostgreSQL backend...", file=sys.stderr)
        adapter = PostgresAdapter(connection_uri=DB_URI)
    except Exception as e:
        print(f"CRITICAL: Failed to initialize PostgreSQL adapter: {e}. Falling back to SQLite.", file=sys.stderr)
        adapter = SQLiteAdapter(db_path=DB_PATH)
else:
    print("Starting MCP server with SQLite backend...", file=sys.stderr)
    adapter = SQLiteAdapter(db_path=DB_PATH)

# --- Pydantic Models for Strong Validation (Poka-Yoke) ---

class FilterModel(BaseModel):
    """Defines a single WHERE condition filter."""
    column: str = Field(..., description="The name of the column to filter on.")
    operator: str = Field("=", description="The SQL comparison operator (e.g., '=', '!=', '<', '>', 'LIKE', 'ILIKE').")
    value: Any = Field(..., description="The value to compare against (parameterized to prevent injection).")

# --- Tools ---

@mcp.tool(name="search")
def search(
    table: Annotated[str, Field(description="The table to query.")],
    columns: Annotated[Optional[List[str]], Field(description="Optional list of columns to return. Returns all if omitted.")] = None,
    filters: Annotated[Optional[List[FilterModel]], Field(description="Optional filter criteria to restrict rows.")] = None,
    limit: Annotated[int, Field(description="Max results to return (hard capped at 100).")] = 20,
    offset: Annotated[int, Field(description="Pagination offset.")] = 0,
    order_by: Annotated[Optional[str], Field(description="Optional column name to sort the rows by.")] = None,
    descending: Annotated[bool, Field(description="Whether to sort descending. Defaults to False (ASC).")] = False
) -> Dict[str, Any]:
    """
    Safely search rows in the database with validation, filtering, ordering, and pagination.
    """
    try:
        # Convert Pydantic filter models to dictionaries for database adapter
        filter_dicts = [f.model_dump() for f in filters] if filters else None
        
        return adapter.search(
            table=table,
            columns=columns,
            filters=filter_dicts,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending
        )
    except ValidationError as e:
        return {"is_error": True, "error": f"Validation Error: {str(e)}"}
    except Exception as e:
        return {"is_error": True, "error": f"Database Query Failed: {str(e)}"}


@mcp.tool(name="insert")
def insert(
    table: Annotated[str, Field(description="The table name to insert data into.")],
    values: Annotated[Dict[str, Any], Field(description="Dictionary of key-value pairs representing column values for insertion.")]
) -> Dict[str, Any]:
    """
    Safely insert a row into the database. Prevents SQL injection by strict column validation.
    """
    try:
        return adapter.insert(table=table, values=values)
    except ValidationError as e:
        return {"is_error": True, "error": f"Validation Error: {str(e)}"}
    except Exception as e:
        return {"is_error": True, "error": f"Database Insert Failed: {str(e)}"}


@mcp.tool(name="aggregate")
def aggregate(
    table: Annotated[str, Field(description="The table name.")],
    metric: Annotated[str, Field(description="Aggregation function: COUNT, SUM, AVG, MIN, or MAX.")],
    column: Annotated[Optional[str], Field(description="Column to aggregate. Required for metrics other than COUNT.")] = None,
    filters: Annotated[Optional[List[FilterModel]], Field(description="Optional conditions to filter before aggregating.")] = None,
    group_by: Annotated[Optional[List[str]], Field(description="Optional list of columns for GROUP BY aggregation.")] = None
) -> Dict[str, Any]:
    """
    Safely execute metrics aggregation queries (such as COUNT, AVG, SUM, MIN, MAX) with GROUP BY.
    """
    try:
        filter_dicts = [f.model_dump() for f in filters] if filters else None
        return adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filter_dicts,
            group_by=group_by
        )
    except ValidationError as e:
        return {"is_error": True, "error": f"Validation Error: {str(e)}"}
    except Exception as e:
        return {"is_error": True, "error": f"Database Aggregation Failed: {str(e)}"}


# --- Resources ---

@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Returns the full detailed database schema metadata (all tables and column details).
    """
    try:
        schema = adapter.get_database_schema()
        return json.dumps({"schema": schema}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Could not fetch database schema: {str(e)}"})


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Returns schema details for a specific database table.
    """
    try:
        # First ensure table is safe/exists
        adapter.validate_table(table_name)
        details = adapter.get_detailed_table_schema(table_name)
        return json.dumps({table_name: details}, indent=2)
    except ValidationError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Could not fetch table schema: {str(e)}"})


if __name__ == "__main__":
    # Run server. Standard FastMCP CLI provides stdio by default,
    # or '--transport sse' for HTTP SSE support automatically.
    mcp.run()
