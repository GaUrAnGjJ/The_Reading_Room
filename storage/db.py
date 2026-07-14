"""Database helpers for the pipeline.

This module provides utilities for loading the processed CSV and populating
an SQLite database used by the API and pipeline tasks.
"""
from pathlib import Path
import sqlite3
from typing import Optional
import pandas as pd

# Configuration
ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV = ROOT / "data" / "processed" / "clean_description.csv"
DB_PATH = ROOT / "storage" / "library.db"
TABLE_NAME = "books"


def load_data(csv_path: Path = INPUT_CSV) -> pd.DataFrame:
    """Load the processed CSV into a DataFrame and normalize column names.

    Returns a DataFrame with at least the columns expected by insert_data:
    ['ISBN','Title','Author_Editor','description','description_source','Year','Acc_Date','Place_Publisher']
    """
    print(f"Loading data from {csv_path}")
    df = pd.read_csv(csv_path, encoding="latin-1", low_memory=False)

    # Normalize column names to a predictable format
    df.columns = [c.strip() for c in df.columns]

    # Some CSVs use different names for place/publisher column
    if "Place_&_Publisher" in df.columns and "Place_Publisher" not in df.columns:
        df = df.rename(columns={"Place_&_Publisher": "Place_Publisher"})

    # Add missing optional columns with None
    for col in ("description_source",):
        if col not in df.columns:
            df[col] = None

    return df


def create_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create the database file (and parent dir) if needed and return a connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    # Use text factory and row factory externally as needed
    print(f"Connected to database at {db_path}")
    return conn


def create_table(conn: sqlite3.Connection) -> None:
    """Create the books table if it does not exist.

    Adds a UNIQUE constraint on isbn so that INSERT OR IGNORE works predictably.
    """
    cursor = conn.cursor()

    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isbn TEXT UNIQUE,
        title TEXT NOT NULL,
        author TEXT,
        description TEXT,
        source TEXT,
        year INTEGER,
        acc_date TEXT,
        place_publisher TEXT,
        poster_url TEXT,
        book_url TEXT
    );
    """)

    conn.commit()
    print("Table ensured.")


def _normalize_row(row: pd.Series) -> tuple:
    """Map a CSV row into the DB tuple in correct order and types."""
    isbn = str(row.get("ISBN", "")).strip() or None
    title = str(row.get("Title", "")).strip() or None
    author = str(row.get("Author_Editor", "")).strip() or None
    description = row.get("description")
    source = row.get("description_source")

    # Year can be float (e.g., 1999.0) — convert to int when possible
    year_raw = row.get("Year")
    year: Optional[int] = None
    try:
        if pd.notna(year_raw):
            year = int(float(year_raw))
    except Exception:
        year = None

    acc_date = row.get("Acc_Date")
    place = row.get("Place_Publisher") if "Place_Publisher" in row.index else row.get("Place_Publisher")
    poster_url = row.get("poster_url")
    book_url = row.get("book_url")

    return (isbn, title, author, description, source, year, acc_date, place, poster_url, book_url)


def insert_data(conn: sqlite3.Connection, df: pd.DataFrame) -> None:
    """Insert rows from DataFrame into the books table.

    Uses executemany for speed and INSERT OR IGNORE to avoid duplicates (isbn unique).
    """
    cursor = conn.cursor()

    insert_sql = f"""
    INSERT OR IGNORE INTO {TABLE_NAME}
    (isbn, title, author, description, source, year, acc_date, place_publisher, poster_url, book_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    tuples = [_normalize_row(row) for _, row in df.iterrows()]

    cursor.executemany(insert_sql, tuples)
    conn.commit()
    print(f"Inserted {cursor.rowcount} rows (attempted {len(tuples)}).")


def verify_data(conn: sqlite3.Connection) -> int:
    """Return count of records in the books table."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME};")
    count = cursor.fetchone()[0]
    print(f"Total records in the books table: {count}")
    return count


def main_db() -> None:
    """Run the full import: load CSV -> ensure table -> insert -> verify."""
    df = load_data(INPUT_CSV)
    conn = create_connection(DB_PATH)
    create_table(conn)
    insert_data(conn, df)
    verify_data(conn)
    conn.close()


if __name__ == "__main__":
    main_db()
