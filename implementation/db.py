import sqlite3
import abc
from typing import Any, Dict, List, Optional, Set

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""
    pass

class BaseDatabaseAdapter(abc.ABC):
    """Abstract Base Class for Database Adapters enforcing safe parameterization."""
    
    def __init__(self, param_placeholder: str):
        self.param_placeholder = param_placeholder
        
    @abc.abstractmethod
    def list_tables(self) -> List[str]:
        """Returns a list of visible tables."""
        pass
        
    @abc.abstractmethod
    def get_table_schema(self, table: str) -> List[str]:
        """Returns a list of column names for a table."""
        pass
        
    @abc.abstractmethod
    def get_detailed_table_schema(self, table: str) -> List[Dict[str, Any]]:
        """Returns detailed schema info for a table."""
        pass
        
    @abc.abstractmethod
    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Executes a SELECT query with parameters and returns rows as dicts."""
        pass
        
    @abc.abstractmethod
    def execute_insert(self, query: str, params: List[Any]) -> int:
        """Executes an INSERT and returns the last inserted ID."""
        pass

    def get_database_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns the full schema of the database."""
        schema = {}
        for table in self.list_tables():
            schema[table] = self.get_detailed_table_schema(table)
        return schema
        
    def validate_table(self, table: str) -> None:
        """Checks if the table name is valid, guarding against SQL injection."""
        if table not in self.list_tables():
            raise ValidationError(f"Table '{table}' does not exist.")
            
    def validate_columns(self, table: str, columns: List[str], schema_cols: List[str]) -> None:
        """Checks if all provided columns exist in the specified table's schema."""
        for col in columns:
            if col not in schema_cols:
                raise ValidationError(f"Column '{col}' does not exist in table '{table}'.")

    def search(
        self,
        table: str,
        columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        limit: int = 20,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = False
    ) -> Dict[str, Any]:
        """Poka-Yoke safe search tool implementation."""
        self.validate_table(table)
        schema_cols = self.get_table_schema(table)
        
        if columns:
            self.validate_columns(table, columns, schema_cols)
            # Safety check: quoting columns to prevent potential issues (identifiers are already validated)
            select_clause = ", ".join([f'"{col}"' for col in columns])
        else:
            select_clause = "*"
            
        where_clauses = []
        params: List[Any] = []
        allowed_operators: Set[str] = {"=", "!=", "<", ">", "<=", ">=", "LIKE", "ILIKE"}
        
        if filters:
            for f in filters:
                col = f.get("column")
                op = f.get("operator", "=").upper()
                val = f.get("value")
                
                if not col or val is None:
                    raise ValidationError("Filter elements must include 'column' and 'value'.")
                    
                if col not in schema_cols:
                    raise ValidationError(f"Filter column '{col}' does not exist in table '{table}'.")
                if op not in allowed_operators:
                    raise ValidationError(f"Operator '{op}' is not supported.")
                    
                where_clauses.append(f'"{col}" {op} {self.param_placeholder}')
                params.append(val)
                
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        order_clause = ""
        if order_by:
            if order_by not in schema_cols:
                raise ValidationError(f"Order by column '{order_by}' does not exist in table '{table}'.")
            order_clause = f'ORDER BY "{order_by}" {"DESC" if descending else "ASC"}'
            
        limit = min(limit, 100)
        
        # Construct limit clause
        query = f'SELECT {select_clause} FROM "{table}" {where_clause} {order_clause} LIMIT {self.param_placeholder} OFFSET {self.param_placeholder}'
        params.extend([limit, offset])
        
        rows = self.execute_query(query, params)
        return {"table": table, "rows": rows}

    def insert(self, table: str, values: Dict[str, Any]) -> Dict[str, Any]:
        """Poka-Yoke safe insert tool implementation."""
        self.validate_table(table)
        schema_cols = self.get_table_schema(table)
        
        if not values:
            raise ValidationError("Insert values cannot be empty.")
            
        self.validate_columns(table, list(values.keys()), schema_cols)
        
        cols_str = ", ".join([f'"{k}"' for k in values.keys()])
        placeholders = ", ".join([self.param_placeholder] * len(values))
        params = list(values.values())
        
        query = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders})'
        
        last_id = self.execute_insert(query, params)
        result = dict(values)
        result["id"] = last_id
        return {"table": table, "inserted": result}
        
    def aggregate(
        self,
        table: str,
        metric: str,
        column: Optional[str] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        group_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Poka-Yoke safe aggregate tool implementation."""
        self.validate_table(table)
        schema_cols = self.get_table_schema(table)
        
        allowed_metrics = {"COUNT", "AVG", "SUM", "MIN", "MAX"}
        metric_upper = metric.upper()
        if metric_upper not in allowed_metrics:
            raise ValidationError(f"Metric '{metric}' is not supported. Use one of {allowed_metrics}.")
            
        if column:
            if column not in schema_cols and column != "*":
                raise ValidationError(f"Column '{column}' does not exist in table '{table}'.")
            agg_col = f'"{column}"' if column != "*" else "*"
        else:
            if metric_upper == "COUNT":
                agg_col = "*"
            else:
                raise ValidationError(f"Metric '{metric}' requires a column.")
                
        select_clause = f"{metric_upper}({agg_col}) AS value"
        
        where_clauses = []
        params: List[Any] = []
        allowed_operators: Set[str] = {"=", "!=", "<", ">", "<=", ">=", "LIKE", "ILIKE"}
        
        if filters:
            for f in filters:
                col = f.get("column")
                op = f.get("operator", "=").upper()
                val = f.get("value")
                if not col or val is None:
                    raise ValidationError("Filter elements must include 'column' and 'value'.")
                if col not in schema_cols:
                    raise ValidationError(f"Filter column '{col}' does not exist.")
                if op not in allowed_operators:
                    raise ValidationError(f"Operator '{op}' is not supported.")
                where_clauses.append(f'"{col}" {op} {self.param_placeholder}')
                params.append(val)
                
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        group_clause = ""
        if group_by:
            self.validate_columns(table, group_by, schema_cols)
            group_cols_str = ", ".join([f'"{g}"' for g in group_by])
            select_clause = f"{group_cols_str}, {select_clause}"
            group_clause = f"GROUP BY {group_cols_str}"
            
        query = f'SELECT {select_clause} FROM "{table}" {where_clause} {group_clause}'
        
        rows = self.execute_query(query, params)
        return {"table": table, "metric": metric_upper, "rows": rows}

class SQLiteAdapter(BaseDatabaseAdapter):
    """Concrete SQLite adapter."""
    def __init__(self, db_path: str = "lab.db"):
        super().__init__(param_placeholder="?")
        self.db_path = db_path
        
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def list_tables(self) -> List[str]:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            return [row["name"] for row in cursor.fetchall()]
            
    def get_table_schema(self, table: str) -> List[str]:
        with self.connect() as conn:
            cursor = conn.cursor()
            # We safely quote table identifiers since SQLite doesn't support placeholder for it.
            # Table exists is guaranteed by higher level checks which use list_tables().
            cursor.execute(f'PRAGMA table_info("{table}")')
            return [row["name"] for row in cursor.fetchall()]
            
    def get_detailed_table_schema(self, table: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f'PRAGMA table_info("{table}")')
            return [dict(row) for row in cursor.fetchall()]
            
    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        p = params or []
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, p)
            return [dict(row) for row in cursor.fetchall()]
            
    def execute_insert(self, query: str, params: List[Any]) -> int:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return int(cursor.lastrowid or 0)

class PostgresAdapter(BaseDatabaseAdapter):
    """Concrete Postgres adapter, fallback to fallback logic if library not loaded."""
    def __init__(self, connection_uri: str = "postgresql://postgres:postgres@localhost:5432/mcp_lab"):
        super().__init__(param_placeholder="%s")
        if not HAS_PSYCOPG2:
            raise RuntimeError("psycopg2 is required for PostgresAdapter but not installed.")
        self.connection_uri = connection_uri
        
    def connect(self):
        return psycopg2.connect(self.connection_uri)
        
    def list_tables(self) -> List[str]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
                return [row["table_name"] for row in cursor.fetchall()]
                
    def get_table_schema(self, table: str) -> List[str]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public'",
                    (table,)
                )
                return [row["column_name"] for row in cursor.fetchall()]
                
    def get_detailed_table_schema(self, table: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(
                    "SELECT column_name as name, data_type as type, is_nullable as notnull "
                    "FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public'",
                    (table,)
                )
                return [dict(row) for row in cursor.fetchall()]
                
    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        p = params or []
        with self.connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                cursor.execute(query, p)
                return [dict(row) for row in cursor.fetchall()]
                
    def execute_insert(self, query: str, params: List[Any]) -> int:
        # Postgres needs explicitly specified RETURNING clause to get ID
        q = query.rstrip(";") + " RETURNING id;"
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(q, params)
                row = cursor.fetchone()
                conn.commit()
                return int(row[0]) if row else 0
