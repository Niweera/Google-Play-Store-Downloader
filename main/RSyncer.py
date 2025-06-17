import logging
import shutil
import subprocess
import sys
from os.path import abspath, join, exists
from config.Config import (
    SSH_KEY_PATH,
    APK_LOCAL_STORE_PATH,
    APK_REMOTE_STORE_PATH,
    SSH_HOST,
    SSH_PORT,
    APP_METADATA_REMOTE_STORE_PATH,
    APP_METADATA_LOCAL_STORE_PATH,
)
from helpers.Logger import EpochFormatter

logger = logging.getLogger("RSyncer:")
formatter = EpochFormatter("[%(asctime)s] [%(name)s] %(message)s")
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[stdout_handler])


class RSyncer:
    def __init__(self, app_id):
        self.app_id = app_id

    def _rsync(self, source, destination):
        if not exists(source):
            raise Exception(f"Source path: [{source}] does not exist")

        command = [
            "rsync",
            "-avz",
            "--checksum",
            "--no-group",
            "--no-owner",
            "-e",
            f"ssh -i {SSH_KEY_PATH} -p {SSH_PORT}",
            source,
            destination,
        ]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode == 0:
            logger.info("Transfer completed successfully.")
            shutil.rmtree(source) if not source.endswith(".json") else os.remove(source)
            logger.info(f"Deleted source path: [{source}]")
        else:
            raise Exception(
                f"An error occurred in [{self.app_id}]: {result.stderr.decode()}"
            )

    def move_apk_files(self):
        logger.info(f"Moving APK files to remote: for app: [{self.app_id}]")
        source = abspath(join(APK_LOCAL_STORE_PATH, self.app_id))
        destination = f"{SSH_HOST}:{APK_REMOTE_STORE_PATH}"
        self._rsync(source, destination)

    def move_app_metadata(self):
        logger.info(
            f"Moving app metadata JSON files to remote: for app: [{self.app_id}]"
        )
        source = abspath(join(APP_METADATA_LOCAL_STORE_PATH, f"{self.app_id}.json"))
        destination = f"{SSH_HOST}:{APP_METADATA_REMOTE_STORE_PATH}/"
        self._rsync(source, destination)
