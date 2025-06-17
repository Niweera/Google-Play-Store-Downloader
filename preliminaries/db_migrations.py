import sqlite3
from os.path import abspath, join, dirname, realpath
from config.Config import SQLITE_DB_NAME

input_apps_path = abspath(join(dirname(dirname(realpath(__file__))), "inputs", ".txt"))
input_apps_path_v2 = abspath(
    join(dirname(dirname(realpath(__file__))), "inputs", ".txt")
)

custom_apps_path = abspath(join(dirname(dirname(realpath(__file__))), "inputs", ".txt"))


def get_db_connection():
    main_db_path = abspath(
        join(dirname(dirname(realpath(__file__))), "databases", SQLITE_DB_NAME)
    )
    return sqlite3.connect(main_db_path)


def create_input_apps_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;
        
        CREATE TABLE IF NOT EXISTS input_apps (
            app_id TEXT NOT NULL PRIMARY KEY,
            downloaded BOOLEAN DEFAULT 0,
            metadata BOOLEAN DEFAULT 0,
            device TEXT DEFAULT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx2_app_id ON input_apps (app_id);
        """
    )
    conn.commit()
    conn.close()


def insert_input_apps(input_apps_file_path):
    conn = get_db_connection()
    cursor = conn.cursor()

    with open(input_apps_file_path, "r") as file:
        app_ids = {(line.strip(),) for line in file if line.strip()}

    cursor.executemany("INSERT OR IGNORE INTO input_apps (app_id) VALUES (?)", app_ids)
    conn.commit()

    inserted_count = conn.total_changes
    conn.close()

    print(f"{inserted_count} rows inserted into input_apps.")


def create_error_apps_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS error_apps (
            app_id TEXT NOT NULL,
            device TEXT NOT NULL,
            error TEXT NOT NULL,
            PRIMARY KEY (app_id, device, error),
            FOREIGN KEY (app_id) REFERENCES input_apps (app_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_error ON error_apps (error);
        CREATE INDEX IF NOT EXISTS idx_app_id ON error_apps (app_id);
        """
    )
    conn.commit()
    conn.close()


def main():
    create_input_apps_table()
    # insert_input_apps(input_apps_path)
    # insert_input_apps(input_apps_path_v2)
    insert_input_apps(custom_apps_path)
    create_error_apps_table()


if __name__ == "__main__":
    main()
