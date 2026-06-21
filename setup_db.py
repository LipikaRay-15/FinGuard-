"""
FinGuard - One-click Database Setup Script
Run this from inside the FinGuard folder:
    python setup_db.py
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

HOST     = os.getenv("MYSQL_HOST", "localhost")
PORT     = int(os.getenv("MYSQL_PORT", 3306))
USER     = os.getenv("MYSQL_USER", "root")
PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME  = os.getenv("MYSQL_DATABASE", "finguard_db")

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "sql", "schema.sql")


def split_sql_statements(sql: str):
    """
    Splits a SQL file into individual executable statements.
    Correctly handles BEGIN...END blocks (triggers, stored procedures)
    by NOT splitting on semicolons inside them.
    """
    statements = []
    current    = []
    depth      = 0          # tracks nesting level of BEGIN...END

    for line in sql.splitlines():
        stripped = line.strip()

        # Skip pure comment lines and blank lines
        if not stripped or stripped.startswith("--"):
            continue

        # Remove inline comments (e.g. "col VARCHAR(10), -- some note")
        if " --" in line:
            line = line[:line.index(" --")]
            stripped = line.strip()

        upper = stripped.upper()

        # Increase depth on BEGIN keyword
        if upper == "BEGIN" or upper.endswith(" BEGIN"):
            depth += 1

        current.append(line)

        # A semicolon at depth 0 marks the end of a standalone statement
        if stripped.endswith(";") and depth == 0:
            stmt = "\n".join(current).strip().rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current = []

        # Decrease depth on END keyword (handles END; and END)
        if upper in ("END;", "END") or upper.startswith("END;"):
            if depth > 0:
                depth -= 1

    # Catch any trailing statement without a final semicolon
    if current:
        stmt = "\n".join(current).strip().rstrip(";").strip()
        if stmt:
            statements.append(stmt)

    return statements


def run():
    print("=" * 60)
    print("  FinGuard Database Setup")
    print("=" * 60)

    # ── Step 1: Create the database ──────────────────────────────
    print(f"\n[1/3] Creating database '{DB_NAME}' ...")
    try:
        conn = mysql.connector.connect(
            host=HOST, port=PORT, user=USER, password=PASSWORD
        )
        cur = conn.cursor()
        cur.execute(f"DROP DATABASE IF EXISTS `{DB_NAME}`")
        cur.execute(f"CREATE DATABASE `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cur.close()
        conn.close()
        print(f"    ✓ Database '{DB_NAME}' created.")
    except mysql.connector.Error as e:
        print(f"    ✗ Failed to create database: {e}")
        print("      Make sure MySQL is running and your .env credentials are correct.")
        return

    # ── Step 2: Run schema ───────────────────────────────────────
    print(f"\n[2/3] Applying schema from sql/schema.sql ...")
    if not os.path.exists(SCHEMA_PATH):
        print(f"    ✗ Schema file not found: {SCHEMA_PATH}")
        return

    try:
        conn = mysql.connector.connect(
            host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB_NAME
        )
        cur = conn.cursor()

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            raw_sql = f.read()

        statements = split_sql_statements(raw_sql)
        ok = skipped = 0

        for stmt in statements:
            try:
                cur.execute(stmt)
                conn.commit()
                ok += 1
            except mysql.connector.Error as e:
                # Silently skip expected errors (e.g. DROP on non-existent objects)
                skipped += 1

        cur.close()
        conn.close()
        print(f"    ✓ Schema applied  ({ok} statements OK, {skipped} skipped).")
    except mysql.connector.Error as e:
        print(f"    ✗ Schema error: {e}")
        return

    # ── Step 3: Verify tables ────────────────────────────────────
    print(f"\n[3/3] Verifying tables ...")
    try:
        conn = mysql.connector.connect(
            host=HOST, port=PORT, user=USER, password=PASSWORD, database=DB_NAME
        )
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

        if tables:
            print(f"    ✓ Tables created: {', '.join(tables)}")
        else:
            print("    ✗ No tables found — something went wrong.")
            return
    except mysql.connector.Error as e:
        print(f"    ✗ Verification error: {e}")
        return

    print("\n" + "=" * 60)
    print("  ✓ Database initialized successfully!")
    print("  Run the app with:  python main.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run()
