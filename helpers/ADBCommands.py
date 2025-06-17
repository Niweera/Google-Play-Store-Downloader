import logging
import multiprocessing
import subprocess
import time
from datetime import datetime, timedelta
from adbutils import adb

logger = logging.getLogger(f"ADBCommands:")


class ADBCommands:
    def __init__(self, config):
        self.config = config
        self.device_serial = self.config["pipeline"]["device_serial"]
        self.adb = self.config["pipeline"]["ADB_BINARY"]
        self.adb_utils = adb.device(self.device_serial)

    def adb_simple_shell(self, *args):
        process = subprocess.run(
            [
                self.adb,
                "-s",
                self.device_serial,
                "shell",
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return process.returncode, process.stdout.decode()

    def adb_simple(self, *args):
        process = subprocess.run(
            [
                self.adb,
                "-s",
                self.device_serial,
                *args,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return process.returncode, process.stdout.decode()

    def installed_packages(self) -> list:
        status, ret = self.adb_simple_shell("pm", "list", "packages")
        if ret is None:
            return []
        package_output = [package for package in ret.split("\n") if package]
        package_list = []
        for item in package_output:
            if item.startswith("package"):
                package_list.append(item.replace("package:", ""))

        return package_list

    def is_package_installed(self, package_name: str) -> bool:
        packages = self.installed_packages()
        if package_name in packages:
            return True
        else:
            return False

    def adb_install_multiple(self, apk_files):
        process = subprocess.run(
            [
                self.adb,
                "-s",
                self.device_serial,
                "install-multiple",
                "-r",
                "-g",
                *apk_files,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,  # set timeout to 1 minutes so that it will not hang on harmful apps
        )
        if process.returncode != 0:
            logger.error(process.stdout.decode())
            raise Exception("Failed to install multiple APKs")
        if process.returncode == 0:
            logger.info(f"Installed multiple APKs: {apk_files}")

    def adb_init(self, command, *args, process_queue=None):
        if self.device_serial is not None:
            adb_cmd = [self.adb, "-s", self.device_serial, command]
        else:
            adb_cmd = [self.adb, command]
        adb_cmd.extend(args)

        logger.debug(adb_cmd)

        try:
            result = subprocess.check_output(adb_cmd, stderr=subprocess.STDOUT).decode(
                "UTF-8", "backslashreplace"
            )
        except Exception as e:
            result = None

        if process_queue is not None:
            process_queue.put(result)

        return result

    def adb_command_timeout(
        self, command, *args, timeout_secs: int = 120, quit_on_fail: bool = False
    ):
        ret = multiprocessing.Queue()
        proc = multiprocessing.Process(
            target=self.adb_init, args=(command, *args), kwargs={"process_queue": ret}
        )

        proc.start()

        end_time = datetime.now() + timedelta(seconds=timeout_secs)
        success = True

        while proc.is_alive():
            time.sleep(2)
            if datetime.now() > end_time:
                proc.terminate()
                proc.join()
                success = False

        if not success and quit_on_fail:
            raise Exception(f"Failed to run adb command: {command} {args}")

        if success:
            return success, ret.get_nowait()
        else:
            return success, None

    def adb_uninstall_apk(self, package_name) -> None:
        ret = self.adb_utils.uninstall(package_name)
        logger.info(f"Uninstalled {package_name}: {ret}")
