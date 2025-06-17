import logging
import multiprocessing
import sys
import time
from copy import deepcopy
from config.Config import ADB_BINARY, apk_source, pipeline_device_map
from main.DBDriver import DBDriver
from main.MainClass import MainClass

logger = logging.getLogger("Main:")
formatter = logging.Formatter("[%(asctime)s] [%(name)s] %(message)s")
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(formatter)
logging.basicConfig(level=logging.INFO, handlers=[stdout_handler])

device_serials = []
for _, serials in pipeline_device_map.items():
    device_serials.extend(serials)


def worker(device_serial, config, app_queue):
    logger.info(
        f"Worker [{device_serial}] started with app queue size: {app_queue.qsize()}"
    )
    db_driver = DBDriver()
    all_devices = set(device_serials)
    total_devices = len(all_devices)
    main_class = None
    try:
        while True:
            if app_queue.empty():
                time.sleep(2)
                continue
            item = app_queue.get()
            if item is None:
                continue
            app_id, error_message = item
            if error_message:
                error_devices = set(
                    db_driver.get_error_devices_for_app(app_id, error_message)
                )
                available_devices = all_devices - error_devices
                if not available_devices:
                    logger.info(
                        f"App [{app_id}] failed with error [{error_message}] on all devices. Skipping..."
                    )
                    continue
                if device_serial in error_devices:
                    app_queue.put((app_id, error_message))
                    time.sleep(1)
                    continue
            if db_driver.check_app_is_downloaded(app_id):
                logger.info(f"App [{app_id}] is already downloaded. Skipping...")
                continue
            if db_driver.is_app_incompatible_on_all_devices(app_id, total_devices):
                logger.info(
                    f"App [{app_id}] marked as incompatible on all devices. Skipping..."
                )
                continue
            config_copy = deepcopy(config)
            config_copy["pipeline"]["device_serial"] = device_serial
            try:
                main_class = MainClass(config_copy, app_id)
                main_class.main_entrypoint()
            except Exception as e:
                error_message = str(e)
                logger.error(
                    f"Error processing app [{app_id}] on device [{device_serial}]: {error_message}"
                )
                existing_devices = db_driver.get_error_devices_for_app(
                    app_id, error_message
                )
                if device_serial not in existing_devices:
                    db_driver.write_error(app_id, device_serial, error_message)
                error_devices = set(
                    db_driver.get_error_devices_for_app(app_id, error_message)
                )
                available_devices = all_devices - error_devices
                if available_devices:
                    app_queue.put((app_id, error_message))
                else:
                    logger.info(
                        f"App [{app_id}] failed with error [{error_message}] on all devices. Skipping..."
                    )
            time.sleep(1)
    finally:
        db_driver.close_connection()
        logger.info(f"Database connection closed for worker [{device_serial}]")
        if main_class:
            main_class.google_play.close()
            logger.info(f"Google Play Store closed in worker [{device_serial}]")
        logger.info(f"Worker [{device_serial}] terminated")


def distribute_apps():
    logger.info("Starting the app download process...")
    db_driver = DBDriver()
    apps_to_run = db_driver.get_apps_to_run(len(set(device_serials)))

    if not apps_to_run:
        logger.info("No apps to run. Exiting...")
        db_driver.close_connection()
        sys.exit(0)

    logger.info(f"Apps to run: [{len(apps_to_run)}]")
    base_config = dict(pipeline=dict(ADB_BINARY=ADB_BINARY, apk_source=apk_source))
    manager = multiprocessing.Manager()
    app_queue = manager.Queue()
    for app_id in apps_to_run:
        app_queue.put((app_id, None))
    processes = []
    for device_serial in device_serials:
        config_copy = deepcopy(base_config)
        config_copy["pipeline"]["device_serial"] = device_serial
        p = multiprocessing.Process(
            target=worker, args=(device_serial, config_copy, app_queue), daemon=True
        )
        p.start()
        processes.append(p)
        logger.info(f"Starting worker for device [{device_serial}]")
    try:
        while True:
            apps_to_run = db_driver.get_apps_to_run(len(set(device_serials)))
            is_all_apps_incompatible = db_driver.check_for_incompatible_apps(
                len(set(device_serials))
            )
            if not apps_to_run:
                logger.info("All apps are downloaded. Exiting...")
                break
            if is_all_apps_incompatible:
                logger.info("All apps are incompatible. Exiting...")
                break
            time.sleep(600)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt detected. Terminating workers...")
    finally:
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        db_driver.close_connection()
        logger.info("Terminating the app download process...")
        sys.exit(0)


if __name__ == "__main__":
    distribute_apps()
