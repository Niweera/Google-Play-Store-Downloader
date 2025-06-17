import requests
import time
import random
import os
import multiprocessing
from itertools import cycle
import pandas as pd

BASEPATH = "<>"
AVAILABLE_PATH = os.path.join(BASEPATH, "temp", "available")
UNAVAILABLE_PATH = os.path.join(BASEPATH, "temp", "unavailable")
os.makedirs(AVAILABLE_PATH, exist_ok=True)
os.makedirs(UNAVAILABLE_PATH, exist_ok=True)

PROXIES = {
    "us": [],
    "in": [],
    "es": [],
}


def check_app_availability(app):
    proxy_cycles = {
        country: cycle(proxy_list) for country, proxy_list in PROXIES.items()
    }
    headers = {"User-Agent": "Mozilla/5.0"}

    for country in PROXIES.keys():
        proxy = next(proxy_cycles[country])
        proxy_url = f"http://{proxy}"
        try:
            res = requests.get(
                f"https://play.google.com/store/apps/details?id={app}",
                headers=headers,
                proxies={"http": proxy_url},
                timeout=10,
            )
            if res.status_code == 200:
                open(
                    os.path.join(AVAILABLE_PATH, f"{app}___{country}.txt"), "w"
                ).close()
                print(f"[{app}] is available in {country}")
                return
            elif res.status_code == 404:
                continue
        except requests.RequestException:
            time.sleep(random.uniform(0.5, 1.5))

    open(os.path.join(UNAVAILABLE_PATH, f"{app}.txt"), "w").close()
    print(f"[{app}] is unavailable")


def main(apps):
    with multiprocessing.Pool(processes=4) as pool:
        pool.map(check_app_availability, apps)


if __name__ == "__main__":
    apps_df = pd.read_csv("<>")
    apps_list = apps_df["app_id"].tolist()
    main(apps_list)
