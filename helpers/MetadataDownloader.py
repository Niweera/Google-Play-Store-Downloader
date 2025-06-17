import json
import logging
import os
import sys
from google_play_scraper import app
from config.Config import APP_METADATA_LOCAL_STORE_PATH
from helpers.Logger import EpochFormatter
from main.RSyncer import RSyncer

logger = logging.getLogger("MetadataDownloader:")
formatter = EpochFormatter("[%(asctime)s] [%(name)s] %(message)s")
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[stdout_handler])


class MetadataDownloader:
    def __init__(self, app_id):
        self.app_id = app_id

    def get_apps_metadata(
        self,
    ) -> bool:
        try:
            result = app(self.app_id, lang="en")
            self.dump_json(result)
            logger.info(f"Metadata for app {self.app_id} downloaded successfully.")
            self.sync_with_remote()
            return True
        except Exception as e:
            logger.error(e)
            return False

    def dump_json(self, data):
        output_apps_data_path = os.path.join(
            APP_METADATA_LOCAL_STORE_PATH, f"{self.app_id}.json"
        )
        with open(output_apps_data_path, "w") as f:
            json.dump(data, f)

    def sync_with_remote(self):
        rsyncer = RSyncer(self.app_id)
        rsyncer.move_app_metadata()
