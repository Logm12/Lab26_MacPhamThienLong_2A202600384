import sqlite3
import time

try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Base SQL for SQLite
SCHEMA_SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    student_code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT NOT NULL,
    course_code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade REAL,
    enrollment_date TEXT DEFAULT CURRENT_DATE,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE(student_id, course_id)
);
"""

# Specific SQL for Postgres
SCHEMA_SQL_POSTGRES = """
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    student_code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS courses (
    id SERIAL PRIMARY KEY,
    course_name TEXT NOT NULL,
    course_code TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS enrollments (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    grade REAL,
    enrollment_date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id),
    UNIQUE(student_id, course_id)
);
"""

SEED_SQL = """
INSERT INTO students (full_name, email, student_code)
VALUES
    ('Nguyen Van A', 'nguyenvana@example.com', 'SV001'),
    ('Tran Thi B', 'tranthib@example.com', 'SV002'),
    ('Le Van C', 'levanc@example.com', 'SV003')
ON CONFLICT DO NOTHING;

INSERT INTO courses (course_name, course_code)
VALUES
    ('Lập trình Python', 'PY101'),
    ('Cơ sở dữ liệu SQL', 'DB101'),
    ('Trí tuệ Nhân tạo', 'AI101')
ON CONFLICT DO NOTHING;

-- SQLite ON CONFLICT DO NOTHING works slightly differently or we can ignore errors individually, 
-- but for Postgres standard INSERT works nicely with ON CONFLICT.
"""

# Because enrollments have foreign keys and SQLite doesn't support standard ON CONFLICT without explicit constraint triggers, 
# we will split seeds or handle them cautiously.
ENROLLMENT_SEEDS = [
    (1, 1, 8.5),
    (1, 2, 9.0),
    (2, 1, 7.0),
    (2, 3, 8.0),
    (3, 2, 9.5),
    (3, 3, 8.8)
]

def create_sqlite_db():
    print("Initializing SQLite database...")
    conn = sqlite3.connect("lab.db")
    cursor = conn.cursor()
    cursor.executescript(SCHEMA_SQL_SQLITE)
    
    # Run seeds manually or with script, avoiding duplicates
    for table in ["students", "courses"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        if cursor.fetchone()[0] == 0:
            if table == "students":
                cursor.executemany(
                    "INSERT INTO students (full_name, email, student_code) VALUES (?, ?, ?)",
                    [
                        ('Nguyen Van A', 'nguyenvana@example.com', 'SV001'),
                        ('Tran Thi B', 'tranthib@example.com', 'SV002'),
                        ('Le Van C', 'levanc@example.com', 'SV003')
                    ]
                )
            elif table == "courses":
                cursor.executemany(
                    "INSERT INTO courses (course_name, course_code) VALUES (?, ?)",
                    [
                        ('Lập trình Python', 'PY101'),
                        ('Cơ sở dữ liệu SQL', 'DB101'),
                        ('Trí tuệ Nhân tạo', 'AI101')
                    ]
                )
    
    cursor.execute("SELECT COUNT(*) FROM enrollments")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO enrollments (student_id, course_id, grade) VALUES (?, ?, ?)",
            ENROLLMENT_SEEDS
        )
        
    conn.commit()
    conn.close()
    print("SQLite database initialized and seeded.")

def create_postgres_db():
    if not HAS_PSYCOPG2:
        print("psycopg2 not available, skipping Postgres initialization.")
        return
        
    print("Connecting to PostgreSQL and initializing...")
    uri = "postgresql://postgres:postgres@localhost:5432/mcp_lab"
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(uri)
            break
        except psycopg2.OperationalError as e:
            if attempt == max_retries - 1:
                print(f"Failed to connect to Postgres: {e}")
                return
            print(f"Postgres not ready yet, retrying in 2s... (attempt {attempt+1}/{max_retries})")
            time.sleep(2)
            
    cursor = conn.cursor()
    cursor.execute(SCHEMA_SQL_POSTGRES)
    
    # Check counts & seed
    for table in ["students", "courses"]:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        if cursor.fetchone()[0] == 0:
            if table == "students":
                cursor.executemany(
                    "INSERT INTO students (full_name, email, student_code) VALUES (%s, %s, %s)",
                    [
                        ('Nguyen Van A', 'nguyenvana@example.com', 'SV001'),
                        ('Tran Thi B', 'tranthib@example.com', 'SV002'),
                        ('Le Van C', 'levanc@example.com', 'SV003')
                    ]
                )
            elif table == "courses":
                cursor.executemany(
                    "INSERT INTO courses (course_name, course_code) VALUES (%s, %s)",
                    [
                        ('Lập trình Python', 'PY101'),
                        ('Cơ sở dữ liệu SQL', 'DB101'),
                        ('Trí tuệ Nhân tạo', 'AI101')
                    ]
                )
                
    cursor.execute("SELECT COUNT(*) FROM enrollments")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO enrollments (student_id, course_id, grade) VALUES (%s, %s, %s)",
            ENROLLMENT_SEEDS
        )
        
    conn.commit()
    cursor.close()
    conn.close()
    print("PostgreSQL database initialized and seeded.")

if __name__ == "__main__":
    create_sqlite_db()
    create_postgres_db()
