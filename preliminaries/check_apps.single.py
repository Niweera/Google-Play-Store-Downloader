import requests
import time
import os
import pandas as pd

BASEPATH = "<>"
AVAILABLE_PATH = os.path.join(BASEPATH, "temp", "available")
UNAVAILABLE_PATH = os.path.join(BASEPATH, "temp", "unavailable")
os.makedirs(AVAILABLE_PATH, exist_ok=True)
os.makedirs(UNAVAILABLE_PATH, exist_ok=True)


def check_app_availability(app):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(
            f"https://play.google.com/store/apps/details?id={app}",
            headers=headers,
            timeout=10,
        )
        if res.status_code == 200:
            open(os.path.join(AVAILABLE_PATH, f"{app}___in.txt"), "w").close()
            print(f"[{app}] is available")
        elif res.status_code == 404:
            open(os.path.join(UNAVAILABLE_PATH, f"{app}.txt"), "w").close()
            print(f"[{app}] is unavailable")
        else:
            print(f"Error in checking [{app}]: [status_code: {res.status_code}]")
    except requests.RequestException as e:
        open(os.path.join(UNAVAILABLE_PATH, f"{app}.txt"), "w").close()
        print(f"[{app}] ERROR:", e)
    time.sleep(0.5)


if __name__ == "__main__":
    apps_df = pd.read_csv("<>")
    apps_list = apps_df["app_id"].tolist()
    for app in apps_list:
        check_app_availability(app)
