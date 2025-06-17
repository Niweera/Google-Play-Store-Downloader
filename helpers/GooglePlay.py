import logging
import os
import re
import tempfile
import time
from os.path import abspath, join
import humanize
from xml.etree import ElementTree
from helpers.ADBCommands import ADBCommands

logger = logging.getLogger("GooglePlay:")


class GooglePlay:
    def __init__(self, config):
        self.config = config
        self.device_serial = config["pipeline"]["device_serial"]
        self.adb = ADBCommands(config)
        self.install_timeout = 1800
        self.install_button_timeout = 20

    def pull_ui_hierarchy(self):
        temp_file_path = abspath(
            join(tempfile.gettempdir(), f"{self.device_serial}_ui.xml")
        )
        self.adb.adb_simple_shell("uiautomator", "dump", "/sdcard/ui.xml")
        self.adb.adb_simple("pull", "/sdcard/ui.xml", temp_file_path)
        if not os.path.exists(temp_file_path) or os.stat(temp_file_path).st_size == 0:
            raise Exception("Failed to retrieve UI hierarchy")
        return ElementTree.parse(temp_file_path).getroot()

    @staticmethod
    def get_coordinates(root_node, attribute, value):
        for node in root_node.iter("node"):
            if node.attrib.get(attribute) == value:
                return re.findall(r"\d+", node.attrib["bounds"])
        return None

    def check_app_incompatible(self):
        error_messages = {
            "App is incompatible": {
                "Your device isn't compatible with this version.",
                "This app isn't available for your device because it was made for an older version of Android.",
                "This phone isn't compatible with this app.",
                "Item not found.",
            },
            "This item isn't available in your country.": {
                "This item isn't available in your country.",
            },
        }

        for node in self.pull_ui_hierarchy().iter("node"):
            text_content = node.attrib.get("text", "") + node.attrib.get(
                "content-desc", ""
            )
            for error_type, errors in error_messages.items():
                if any(error in text_content for error in errors):
                    raise Exception(error_type)
            # for a special case, where no messages in the UI hierarchy
            if (
                node.attrib.get("resource-id", "")
                == "com.android.vending:id/0_resource_name_obfuscated"
            ):
                raise Exception("App is incompatible")

    def download_from_store(self, app_id):
        self.adb.adb_simple_shell(
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            f"market://details?id={app_id}",
        )
        time.sleep(5)
        timeout = 0
        while timeout <= self.install_button_timeout:
            logger.info(
                f"[{self.device_serial}] Waiting for install button (10s) [time left: {self.install_button_timeout - timeout}]"
            )
            root_node = self.pull_ui_hierarchy()
            install_button_cord = self.get_coordinates(
                root_node, "content-desc", "Install"
            )

            if install_button_cord:
                x = round(
                    (int(install_button_cord[0]) + int(install_button_cord[2])) / 2
                )
                y = round(
                    (int(install_button_cord[1]) + int(install_button_cord[3])) / 2
                )
                self.adb.adb_simple_shell("input", "tap", str(x), str(y))
                logger.info(f"Install button clicked: {app_id}")
                return self.check_for_install_complete(app_id)
            self.check_app_incompatible()
            time.sleep(10)
            timeout += 10
        raise Exception("Failed to find install button")

    def check_for_install_complete(self, app_id):
        timeout = 0
        while timeout < self.install_timeout:
            logger.info(
                f"[{self.device_serial}] Waiting for install to complete (10s) [time left: {self.install_timeout - timeout}]"
            )
            time.sleep(10)
            root_node = self.pull_ui_hierarchy()
            if self.get_coordinates(
                root_node, "content-desc", "Uninstall"
            ) or self.get_coordinates(root_node, "text", "Uninstall"):
                return
            if self.get_coordinates(root_node, "content-desc", "Update"):
                raise Exception("Update available")
            if self.get_coordinates(root_node, "text", "Got it"):
                raise Exception("Age verification required")
            if self.get_coordinates(root_node, "text", "Complete account setup"):
                self.handle_account_setup(app_id)
            if self.adb.is_package_installed(app_id):
                return
            timeout += 10
        raise Exception("Installation timeout")

    def handle_account_setup(self, app_id):
        root_node = self.pull_ui_hierarchy()
        for button in ["Continue", "Skip", "Install"]:
            coords = self.get_coordinates(root_node, "text", button)
            if coords:
                x = round((int(coords[0]) + int(coords[2])) / 2)
                y = round((int(coords[1]) + int(coords[3])) / 2)
                self.adb.adb_simple_shell("input", "tap", str(x), str(y))
                logger.info(f"{button} button clicked: {app_id}")
                time.sleep(10)
                root_node = self.pull_ui_hierarchy()

    def _get_apk_path(self, app_id):
        paths = []
        status, res = self.adb.adb_simple_shell("pm", "path", app_id)
        for line in res.splitlines():
            if line.startswith("package:"):
                paths.append(line.split("package:")[1])
        return paths

    def pull_apk(self, app_id):
        paths = self._get_apk_path(app_id)
        app_pull_path = abspath(join(self.config["pipeline"]["apk_source"], app_id))
        os.makedirs(app_pull_path, exist_ok=True)
        _, _, files = next(os.walk(app_pull_path))
        if len(files) != len(paths):
            for path in paths:
                file_name = path.split("/")[-1]
                size = self.adb.adb_utils.sync.pull(
                    path, abspath(join(app_pull_path, file_name))
                )
                logger.info(f"Pulled {path} with size {humanize.naturalsize(size)}")

    def close(self):
        self.adb.adb_simple_shell("am", "force-stop", "com.android.vending")
