# Google-Play-Store-Downloader

A fully automated script to download apps from a given text file using distributed queue of real or virtual devices.

## Setup Guide

1. Install SQLite3

```bash
sudo apt install sqlite3  # For Ubuntu
brew install sqlite3      # For macOS
```

2. Install necessary requirements

```bash
pip install -r requirements.txt
```

3. Run DB migrations

Add the list of apps to download in /inputs/apk_list.txt file.

```bash
python preliminaries/db_migrations.py
```

4. Add config details

`/config/Config.py`

```python
SSH_KEY_PATH = ""
ADB_BINARY = ""  # path to ADB binary
apk_source = ""  # path to store downloaded APKs locally
pipeline_device_map = {
    "pipeline-1": [],
}
APK_REMOTE_STORE_PATH = ""
APK_LOCAL_STORE_PATH = ""
SSH_HOST = ""
SSH_PORT = 22
```

Sample config file is at `/config/Config.env.py`.


5. Run the script

```bash
python3 /main.py
```

6. Run the UI to monitor the progress

```bash
streamlit run /ui/app.py
```