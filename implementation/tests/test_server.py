import pytest
import sqlite3
from db import SQLiteAdapter, ValidationError
from mcp_server import search, database_schema, table_schema, FilterModel

# Fixture to prepare a fresh test database
@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE students (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        age INTEGER
    );
    INSERT INTO students (id, name, age) VALUES (1, 'John Doe', 20);
    INSERT INTO students (id, name, age) VALUES (2, 'Jane Smith', 22);
    """)
    conn.commit()
    conn.close()
    
    return SQLiteAdapter(db_path=str(db_file))

# Directly test the database adapter
def test_adapter_list_tables(test_db):
    tables = test_db.list_tables()
    assert "students" in tables

def test_adapter_search_all(test_db):
    result = test_db.search(table="students")
    assert result["table"] == "students"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["name"] == "John Doe"

def test_adapter_search_filtered(test_db):
    filters = [{"column": "name", "operator": "=", "value": "Jane Smith"}]
    result = test_db.search(table="students", filters=filters)
    assert len(result["rows"]) == 1
    assert result["rows"][0]["age"] == 22

def test_adapter_search_invalid_table(test_db):
    with pytest.raises(ValidationError) as excinfo:
        test_db.search(table="non_existent")
    assert "does not exist" in str(excinfo.value)

def test_adapter_search_invalid_column(test_db):
    with pytest.raises(ValidationError) as excinfo:
        test_db.search(table="students", columns=["invalid_col"])
    assert "does not exist" in str(excinfo.value)

def test_adapter_insert(test_db):
    new_row = {"name": "Bob Johnson", "age": 25}
    res = test_db.insert(table="students", values=new_row)
    assert res["inserted"]["id"] > 0
    
    # Verify insertion
    rows = test_db.search(table="students")["rows"]
    assert len(rows) == 3

def test_adapter_aggregate(test_db):
    res = test_db.aggregate(table="students", metric="AVG", column="age")
    assert res["metric"] == "AVG"
    assert res["rows"][0]["value"] == 21.0 # (20 + 22)/2

def test_adapter_aggregate_count(test_db):
    res = test_db.aggregate(table="students", metric="COUNT")
    assert res["metric"] == "COUNT"
    assert res["rows"][0]["value"] == 2

# Monkeypatch the adapter in mcp_server to use the test_db and test tool execution

def test_mcp_search_tool(test_db, monkeypatch):
    import mcp_server
    monkeypatch.setattr(mcp_server, "adapter", test_db)
    
    # Testing tool with Pydantic models
    filters = [FilterModel(column="age", operator=">", value=21)]
    res = search(table="students", filters=filters)
    
    assert "rows" in res
    assert len(res["rows"]) == 1
    assert res["rows"][0]["name"] == "Jane Smith"

def test_mcp_search_tool_error_handling(test_db, monkeypatch):
    import mcp_server
    monkeypatch.setattr(mcp_server, "adapter", test_db)
    
    # Test invalid column via the tool interface
    res = search(table="students", columns=["hacker_col"])
    assert res.get("is_error") is True
    assert "Validation Error" in res["error"]

def test_mcp_schema_resources(test_db, monkeypatch):
    import mcp_server
    monkeypatch.setattr(mcp_server, "adapter", test_db)
    
    db_res = database_schema()
    assert "students" in db_res
    
    tbl_res = table_schema(table_name="students")
    assert "students" in tbl_res
    
    err_res = table_schema(table_name="ghost_table")
    assert "error" in err_res
