"""Database connection, schema creation, and migration utilities."""
import json
import os
import sqlite3
import threading

from config import Config

_lock = threading.RLock()
_local = threading.local()


def get_db():
    """Get a thread-local SQLite connection (or MySQL if configured)."""
    if Config.DB_TYPE == "mysql":
        import pymysql
        import pymysql.cursors

        return pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )

    # SQLite
    db_path = Config.DATABASE_PATH
    if db_path != ":memory:" and not os.path.isabs(db_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, db_path)

    # Cache connection per thread
    conn = getattr(_local, "conn", None)
    cached_path = getattr(_local, "path", None)
    if conn is None or cached_path != db_path:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        _local.conn = conn
        _local.path = db_path
    return conn


def init_db():
    """Create tables if they don't exist and run non-destructive migrations."""
    with _lock:
        conn = get_db()
        c = conn.cursor()

        # 1. Students table
        c.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                rollNo TEXT,
                email TEXT UNIQUE NOT NULL,
                department TEXT,
                cgpa REAL,
                backlogs INTEGER DEFAULT 0,
                year INTEGER DEFAULT 4,
                skills TEXT DEFAULT '',
                placed INTEGER DEFAULT 0
            )
        """)

        # Check existing columns and migrate if missing
        c.execute("PRAGMA table_info(students)")
        s_cols = {r[1]: r[2] for r in c.fetchall()}
        for col, col_type in [
            ("rollNo", "TEXT"),
            ("backlogs", "INTEGER DEFAULT 0"),
            ("year", "INTEGER DEFAULT 4"),
            ("skills", "TEXT DEFAULT ''"),
            ("placed", "INTEGER DEFAULT 0"),
        ]:
            if col not in s_cols:
                c.execute(f"ALTER TABLE students ADD COLUMN {col} {col_type}")

        # Normalize existing department naming
        c.execute("UPDATE students SET department = 'AI & DS' WHERE department IN ('AI&DS', 'AI & DS')")

        # 2. Jobs table
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT,
                job_role TEXT,
                package REAL,
                location TEXT DEFAULT 'Chennai',
                minCgpa REAL,
                minimum_cgpa REAL,
                maxBacklogs INTEGER DEFAULT 0,
                departments TEXT,
                deadline TEXT,
                status TEXT DEFAULT 'Open'
            )
        """)

        c.execute("PRAGMA table_info(jobs)")
        j_cols = {r[1]: r[2] for r in c.fetchall()}
        for col, col_type in [
            ("role", "TEXT"),
            ("job_role", "TEXT"),
            ("location", "TEXT DEFAULT 'Chennai'"),
            ("minCgpa", "REAL"),
            ("minimum_cgpa", "REAL"),
            ("maxBacklogs", "INTEGER DEFAULT 0"),
            ("departments", "TEXT"),
            ("deadline", "TEXT"),
            ("status", "TEXT DEFAULT 'Open'"),
        ]:
            if col not in j_cols:
                c.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_type}")

        # Sync role and minCgpa with job_role / minimum_cgpa if needed
        c.execute("UPDATE jobs SET role = job_role WHERE (role IS NULL OR role = '') AND job_role IS NOT NULL")
        c.execute("UPDATE jobs SET job_role = role WHERE (job_role IS NULL OR job_role = '') AND role IS NOT NULL")
        c.execute("UPDATE jobs SET minCgpa = minimum_cgpa WHERE minCgpa IS NULL AND minimum_cgpa IS NOT NULL")
        c.execute("UPDATE jobs SET minimum_cgpa = minCgpa WHERE minimum_cgpa IS NULL AND minCgpa IS NOT NULL")
        c.execute("UPDATE jobs SET status = 'Open' WHERE status IS NULL OR status = ''")

        # 3. Applications table
        c.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                studentId INTEGER,
                student_id INTEGER,
                jobId INTEGER,
                job_id INTEGER,
                appliedOn TEXT,
                status TEXT DEFAULT 'Applied',
                FOREIGN KEY(studentId) REFERENCES students(id),
                FOREIGN KEY(jobId) REFERENCES jobs(id)
            )
        """)

        c.execute("PRAGMA table_info(applications)")
        a_cols = {r[1]: r[2] for r in c.fetchall()}
        for col, col_type in [
            ("studentId", "INTEGER"),
            ("student_id", "INTEGER"),
            ("jobId", "INTEGER"),
            ("job_id", "INTEGER"),
            ("appliedOn", "TEXT"),
            ("status", "TEXT DEFAULT 'Applied'"),
        ]:
            if col not in a_cols:
                c.execute(f"ALTER TABLE applications ADD COLUMN {col} {col_type}")

        c.execute("UPDATE applications SET studentId = student_id WHERE studentId IS NULL AND student_id IS NOT NULL")
        c.execute("UPDATE applications SET student_id = studentId WHERE student_id IS NULL AND studentId IS NOT NULL")
        c.execute("UPDATE applications SET jobId = job_id WHERE jobId IS NULL AND job_id IS NOT NULL")
        c.execute("UPDATE applications SET job_id = jobId WHERE job_id IS NULL AND jobId IS NOT NULL")
        c.execute("UPDATE applications SET status = 'Interview Scheduled' WHERE status = 'Interview'")

        # 4. Interviews table
        c.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                applicationId INTEGER UNIQUE,
                date TEXT,
                time TEXT,
                mode TEXT DEFAULT 'Online',
                venue TEXT,
                FOREIGN KEY(applicationId) REFERENCES applications(id)
            )
        """)

        conn.commit()
