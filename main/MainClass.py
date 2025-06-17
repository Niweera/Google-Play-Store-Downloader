import logging
import sys
import time
from helpers.ADBCommands import ADBCommands
from helpers.GooglePlay import GooglePlay
from helpers.Logger import EpochFormatter
from helpers.MetadataDownloader import MetadataDownloader
from main.DBDriver import DBDriver
from main.RSyncer import RSyncer

logger = logging.getLogger("GooglePlayDownloader:")
formatter = EpochFormatter("[%(asctime)s] [%(name)s] %(message)s")
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[stdout_handler])


class MainClass:
    def __init__(self, config, app_id):
        self.app_id = app_id
        self.device_serial = config["pipeline"]["device_serial"]
        self.config = config
        self.adb = ADBCommands(config=self.config)
        self.google_play = GooglePlay(self.config)
        self.db_driver = DBDriver()
        self.rsyncer = RSyncer(self.app_id)
        self.metadata_downloader = MetadataDownloader(self.app_id)

    def main_entrypoint(self):
        self.db_driver.set_app_downloading(self.app_id, self.device_serial)
        self.turn_on_the_device_screen()
        logger.info(f"[{self.device_serial}] Processing app: [{self.app_id}]")
        if not self.adb.is_package_installed(self.app_id):
            self.google_play.download_from_store(self.app_id)
        self.pull_application()
        self.uninstall_app()
        self.rsyncer.move_apk_files()
        is_metadata_downloaded = self.metadata_downloader.get_apps_metadata()
        self.db_driver.mark_app_downloaded(self.app_id, is_metadata_downloaded)
        self.google_play.close()
        time.sleep(10)
        logger.info(f"[{self.device_serial}] Finished processing app: [{self.app_id}]")

    def turn_on_the_device_screen(self):
        screen_off = self.adb.adb_utils.shell(
            'dumpsys power | grep "mHoldingDisplay" | grep "false"'
        )
        if screen_off:
            self.adb.adb_utils.shell("input keyevent KEYCODE_POWER")
            time.sleep(1)
            self.adb.adb_utils.shell("input keyevent 82")

    def pull_application(self):
        if self.adb.is_package_installed(self.app_id):
            self.google_play.pull_apk(self.app_id)
        else:
            raise Exception(f"App: [{self.app_id}] is not installed")

    def uninstall_app(self):
        self.adb.adb_uninstall_apk(self.app_id)
