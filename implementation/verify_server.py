import os
from db import SQLiteAdapter, PostgresAdapter, BaseDatabaseAdapter, ValidationError

def run_verification_for(adapter: BaseDatabaseAdapter, name: str):
    print(f"=== VERIFYING BACKEND: {name} ===")
    
    # 1. Verify Table Discovery
    try:
        tables = adapter.list_tables()
        print(f"[PASS] Successfully listed tables: {tables}")
        assert "students" in tables
        assert "courses" in tables
        assert "enrollments" in tables
    except Exception as e:
        print(f"[FAIL] Table Discovery: {e}")
        return

    # 2. Verify Schema Queries
    try:
        schema = adapter.get_table_schema("students")
        print(f"[PASS] Successfully retrieved schema for 'students': {schema}")
        assert "id" in schema
        assert "full_name" in schema
    except Exception as e:
        print(f"[FAIL] Table Schema: {e}")
        
    # 3. Verify Safe Search
    try:
        res = adapter.search(table="students")
        print(f"[PASS] Successfully searched 'students'. Rows returned: {len(res.get('rows', []))}")
        assert len(res["rows"]) >= 3 # Seed has 3 rows
    except Exception as e:
        print(f"[FAIL] Base Search: {e}")

    # 4. Verify Search with Filter
    try:
        filters = [{"column": "email", "operator": "=", "value": "nguyenvana@example.com"}]
        res = adapter.search(table="students", filters=filters)
        rows = res.get("rows", [])
        print(f"[PASS] Search with filter returned {len(rows)} row(s)")
        assert len(rows) == 1
        assert rows[0]["full_name"] == "Nguyen Van A"
    except Exception as e:
        print(f"[FAIL] Filtered Search: {e}")

    # 5. Verify Injection Safety (Expect ValidationError)
    try:
        adapter.search(table="students", columns=["id; DROP TABLE students; --"])
        print("[FAIL] SQL Injection Prevention: Security vulnerability! The invalid column request succeeded without raising exception!")
    except ValidationError as e:
        print(f"[PASS] SQL Injection Prevention: Successfully rejected invalid column with error: {e}")
    except Exception as e:
        print(f"[FAIL] Injection safety raised unexpected exception: {e}")

    # 6. Verify Aggregate Functions
    try:
        res = adapter.aggregate(table="enrollments", metric="AVG", column="grade")
        val = res["rows"][0]["value"]
        print(f"[PASS] Aggregate verification: Avg grade in enrollments: {val}")
        assert val is not None
    except Exception as e:
        print(f"[FAIL] Aggregation query: {e}")

    # 7. Verify Insert Capability
    try:
        import time
        ts = int(time.time() * 1000) % 100000 # Short millisecond timestamp
        dummy_email = f"test_insert_{name.lower()}_{ts}@example.com"
        res = adapter.insert(table="students", values={
            "full_name": "Test Automated User",
            "email": dummy_email,
            "student_code": f"T{name[:2].upper()}{ts}"
        })
        inserted_id = res["inserted"]["id"]
        print(f"[PASS] Row inserted successfully into 'students', ID: {inserted_id}")
        assert inserted_id > 0
        
        # Clean up or confirm it exists
        check = adapter.search(table="students", filters=[{"column": "email", "operator": "=", "value": dummy_email}])
        assert len(check["rows"]) == 1
    except Exception as e:
        print(f"[FAIL] Insert verification: {e}")

    print(f"=== COMPLETED VERIFICATION FOR {name} ===\n")


def main():
    # Run SQLite tests
    db_path = "lab.db"
    if os.path.exists(db_path):
        adapter = SQLiteAdapter(db_path)
        run_verification_for(adapter, "SQLite")
    else:
        print(f"[WARN] SQLite lab.db not found at {db_path}. Skipping SQLite live verification.")

    # Run Postgres tests if available
    try:
        adapter = PostgresAdapter()
        run_verification_for(adapter, "PostgreSQL")
    except Exception as e:
        print(f"[INFO] Skipping PostgreSQL live verification. (Reason: {e})")

if __name__ == "__main__":
    main()
