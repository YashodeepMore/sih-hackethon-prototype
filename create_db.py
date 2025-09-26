import pandas as pd
import sqlite3
import os

# --- Configuration ---
CSV_FILE = "argo_indian_ocean_export.csv"
DB_FILE = "argo_data.db"
TABLE_NAME = "argo_data"
# ---------------------

def create_database():
    """
    Reads data from the CSV and loads it into a new SQLite database file.
    """
    if not os.path.exists(CSV_FILE):
        print(f"Error: The file '{CSV_FILE}' was not found.")
        return

    print(f"Reading data from '{CSV_FILE}'...")
    df = pd.read_csv(CSV_FILE)

    print(f"Creating SQLite database at '{DB_FILE}'...")
    conn = sqlite3.connect(DB_FILE)

    print(f"Writing data to table '{TABLE_NAME}'...")
    df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)

    conn.close()
    print(f"\nSuccess! Database '{DB_FILE}' created and is ready for use.")

if __name__ == "__main__":
    create_database()

