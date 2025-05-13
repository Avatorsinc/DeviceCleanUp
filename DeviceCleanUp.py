import os
import json
import csv
import time
import logging
import requests

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

#COonfig go to .env and replace credentials
load_dotenv()
API_KEY      = os.getenv("API_KEY")
EMAIL        = os.getenv("MY_EMAIL")
PASSWORD     = os.getenv("MY_PASSWORD")

DEVICE_URL    = "https://salling.eu.suremdm.io/api/v2/devicegrid"
DELETE_URL    = "https://salling.eu.suremdm.io/api/v2/device/delete"

OUTPUT_DIR    = r"C:\danishcab"
ALL_JSON      = os.path.join(OUTPUT_DIR, "all_devices.json")
STALE_JSON    = os.path.join(OUTPUT_DIR, "stale_devices.json")
STALE_CSV     = os.path.join(OUTPUT_DIR, "stale_devices.csv")

PAGE_LIMIT    = 1000
#here is part of days from last deivce time change as needed
STALE_DAYS    = 60

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS       = {'ApiKey': API_KEY, 'Content-Type': 'application/json'}
CREDENTIALS   = (EMAIL, PASSWORD)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger()

def parse_timestamp(ts_str):
    """
    Parse multiple timestamp formats into a UTC datetime.
    """
    fmts = [
        "%m/%d/%Y %I:%M:%S %p",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(ts_str, fmt)
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            continue
    raise ValueError(f"Unrecognized timestamp format: {ts_str}")

def fetch_all_devices():
    all_devs = []
    offset = 0

    while True:
        log.info(f"Fetching devices offset={offset}")
        payload = {
            "ID": "AllDevices",
            "IsTag": False,
            "SortColumn": "DeviceName",
            "SortOrder": "asc",
            "Limit": PAGE_LIMIT,
            "Offset": offset,
            "IsSearch": True,
            "IsIncludedBlackListed": False,
            "AdvanceSearch": False,
            "EnableDeviceGlobalSearch": True,
            "SearchValue": "%"
        }

        for attempt in range(1, 4):
            try:
                r = requests.post(
                    DEVICE_URL,
                    auth=CREDENTIALS,
                    json=payload,
                    headers=HEADERS,
                    timeout=60
                )
                r.raise_for_status()
                break
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                log.warning(f"Timeout/error on offset {offset}, attempt {attempt}/3: {e}")
                time.sleep(2 ** attempt)
        else:
            log.error(f"Failed to fetch offset {offset} after 3 attempts, aborting.")
            return all_devs

        body = r.json()
        if not body.get("status", False):
            log.error(f"API returned status=false: {body.get('message')}")
            break

        rows = body.get("data", {}).get("rows", [])
        log.info(f" → Retrieved {len(rows)} devices")
        if not rows:
            break

        all_devs.extend(rows)
        offset += PAGE_LIMIT

    with open(ALL_JSON, "w", encoding="utf-8") as f:
        json.dump(all_devs, f, indent=2, default=str)
    log.info(f"Saved {len(all_devs)} total devices to {ALL_JSON}")
    return all_devs

#filtering from fetch

def filter_stale(devices):
    cutoff = datetime.utcnow() - timedelta(days=STALE_DAYS)
    stale = []

    for d in devices:
        ts = d.get("DeviceTimeStamp")
        if not ts:
            log.warning(f"Skipping {d.get('DeviceID')}: no timestamp")
            continue
        try:
            dt = parse_timestamp(ts)
        except ValueError as e:
            log.warning(f"{e} for {d.get('DeviceID')}")
            continue

        if dt < cutoff:
            stale.append({
                "DeviceID":        d.get("DeviceID"),
                "DeviceName":      d.get("DeviceName"),
                "DeviceTimeStamp": ts
            })

    stale.sort(key=lambda x: parse_timestamp(x["DeviceTimeStamp"]))
    return stale

#save filtered out device, you might verify in all of them are ok to remove

f def save_stale(stale_list):
    if not stale_list:
        log.info("No stale devices to save.")
        return

    with open(STALE_JSON, "w", encoding="utf-8") as f:
        json.dump(stale_list, f, indent=2)
    log.info(f"Wrote {len(stale_list)} stale devices to {STALE_JSON}")

    with open(STALE_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["DeviceID","DeviceName","DeviceTimeStamp"])
        writer.writeheader()
        writer.writerows(stale_list)
    log.info(f"Wrote {len(stale_list)} stale devices to {STALE_CSV}")

#here is part to move them from active to recycle bin

def delete_stale_devices(device_ids):
    if not device_ids:
        log.info("No devices to move to recycle bin.")
        return

    id_csv = ",".join(device_ids)
    payload = {"Action":"SEND_TO_DELETED_LIST","DeviceId":id_csv}

    try:
        r = requests.put(DELETE_URL, auth=CREDENTIALS, headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        log.info(f"Moved {len(device_ids)} devices to recycle bin.")
    except Exception as e:
        log.error(f"Failed recycle-bin move: {e}")

#recycle bin clean up (see below for verification code)

def force_delete_devices(device_ids, verification_msg):
    """
    Permanently deletes devices from recycle bin.
    verification_msg: code you supply (e.g. based on device count)
    """
    if not device_ids:
        log.info("No devices to force-delete.")
        return

    id_csv = ",".join(device_ids)
    payload = {
        "Action": "FORCEDELETE_DEVICE",
        "DeviceId": id_csv,
        "VerificationMsg": verification_msg
    }

    try:
        r = requests.put(DELETE_URL, auth=CREDENTIALS, headers=HEADERS, json=payload, timeout=60)
        r.raise_for_status()
        log.info(f"Permanently deleted {len(device_ids)} devices.")
    except Exception as e:
        log.error(f"Failed force delete: {e}")

def main():
    devices = fetch_all_devices()

    log.info("Filtering stale devices…")
    stale = filter_stale(devices)

    total = len(stale)
    print(f"\nTotal stale devices (>{STALE_DAYS} days): {total}\n")
    log.info(f"Found {total} stale devices")

    save_stale(stale)

    #Move to recycle bin log
    log.info("Moving stale devices to recycle bin…")
    delete_stale_devices([r["DeviceID"] for r in stale])

    #Prompt for verification code to force-delete (number of devices)
    if stale:
        code = os.getenv("FORCE_DELETE_VERIFICATION_CODE")
        if not code:
            code = input("Enter verification code to permanently delete these devices: ")
        force_delete_devices([r["DeviceID"] for r in stale], code)

    for rec in stale:
        log.info(f"[{rec['DeviceID']}] {rec['DeviceName']} → {rec['DeviceTimeStamp']}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("Script failed:")
        exit(1)
