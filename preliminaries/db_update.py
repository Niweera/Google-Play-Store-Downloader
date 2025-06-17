import sqlite3
from os.path import abspath, join, dirname, realpath
from config.Config import SQLITE_DB_NAME

completed_apps_path = abspath(
    join(dirname(dirname(realpath(__file__))), "intermediaries", ".txt")
)


def get_db_connection():
    main_db_path = abspath(
        join(dirname(dirname(realpath(__file__))), "databases", SQLITE_DB_NAME)
    )
    return sqlite3.connect(main_db_path)


def update_downloaded_apps():
    conn = get_db_connection()
    cursor = conn.cursor()

    with open(completed_apps_path, "r") as file:
        app_ids = {line.strip() for line in file if line.strip()}

    cursor.executemany(
        "UPDATE input_apps SET downloaded = 1 WHERE app_id = ?",
        [(app_id,) for app_id in app_ids],
    )

    conn.commit()
    updated_count = conn.total_changes
    conn.close()

    print(f"{updated_count} rows updated in input_apps (downloaded = 1).")


def main():
    update_downloaded_apps()


if __name__ == "__main__":
    main()
