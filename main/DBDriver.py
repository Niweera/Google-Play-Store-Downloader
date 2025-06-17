import sqlite3
from os.path import abspath, join, dirname, realpath
from config.Config import SQLITE_DB_NAME


class DBDriver:
    def __init__(self):
        main_db_path = abspath(
            join(dirname(dirname(realpath(__file__))), "databases", SQLITE_DB_NAME)
        )
        self.connection = sqlite3.connect(main_db_path)

    def get_apps_to_run(self, total_devices):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT DISTINCT i.app_id
            FROM input_apps i
            LEFT JOIN error_apps e ON i.app_id = e.app_id
            WHERE i.downloaded = 0
            GROUP BY e.error, i.app_id
            HAVING COUNT(DISTINCT e.device) < ? OR COUNT(e.device) = 0;
            """,
            (total_devices,),
        )
        app_ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return app_ids

    def check_app_is_downloaded(self, app_id):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT downloaded
            FROM input_apps
            WHERE app_id = ?;
            """,
            (app_id,),
        )
        downloaded = cursor.fetchone()
        cursor.close()
        return bool(downloaded[0]) if downloaded else False

    def is_app_incompatible_on_all_devices(self, app_id, total_devices):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(DISTINCT device)
            FROM error_apps
            WHERE app_id = ? AND error = 'App is incompatible';
            """,
            (app_id,),
        )
        count = cursor.fetchone()[0]
        cursor.close()
        return count >= total_devices

    def write_error(self, app_id, device_serial, error):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO error_apps (app_id, device, error)
            VALUES (?, ?, ?);
            """,
            (app_id, device_serial, error),
        )
        self.connection.commit()
        cursor.close()

    def mark_app_downloaded(self, app_id, is_metadata_downloaded=False):
        cursor = self.connection.cursor()

        if is_metadata_downloaded:
            cursor.execute(
                """
                UPDATE input_apps
                SET downloaded = 1, metadata = 1
                WHERE app_id = ?;
                """,
                (app_id,),
            )
        else:
            cursor.execute(
                """
                UPDATE input_apps
                SET downloaded = 1
                WHERE app_id = ?;
                """,
                (app_id,),
            )

        cursor.execute(
            """
            DELETE FROM error_apps
            WHERE app_id = ?;
            """,
            (app_id,),
        )

        self.connection.commit()
        cursor.close()

    def set_app_downloading(self, app_id, device_serial):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            UPDATE input_apps
            SET device = ?
            WHERE app_id = ?;
            """,
            (device_serial, app_id),
        )
        self.connection.commit()
        cursor.close()

    def get_error_devices_for_app(self, app_id, error):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT device FROM error_apps WHERE app_id = ? AND error = ?;",
            (app_id, error),
        )
        devices = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return devices

    def check_for_incompatible_apps(self, total_devices):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT 
            NOT EXISTS (
                SELECT DISTINCT i.app_id
                FROM input_apps i
                LEFT JOIN error_apps e ON i.app_id = e.app_id
                WHERE i.downloaded = 0
                GROUP BY e.error, i.app_id
                HAVING COUNT(DISTINCT e.device) < ? OR COUNT(e.device) = 0
                EXCEPT
                SELECT DISTINCT ea.app_id
                FROM error_apps ea
                WHERE ea.app_id IN (
                    SELECT app_id FROM input_apps WHERE downloaded = 0
                )
                AND ea.error = 'App is incompatible'
                GROUP BY ea.error, ea.app_id
                HAVING COUNT(DISTINCT ea.device) = ?
            ) AS is_subset;
            """,
            (total_devices, total_devices),
        )
        result = cursor.fetchone()
        cursor.close()
        return bool(result[0]) if result else False

    def close_connection(self):
        if self.connection:
            self.connection.close()
