# SureMDM Device Cleanup Script

This repository contains a Python script to automate the identification and cleanup of stale devices in SureMDM. It:

* Fetches all devices via the SureMDM API
* Filters out devices not seen in the last *N* days (default: 60)
* Saves lists of stale devices to JSON and CSV
* Moves stale devices to the Recycle Bin
* Optionally performs a permanent (`FORCEDELETE`) deletion with verification

---

## 🚀 Features

* **Pagination & Retry**: Automatically pages through all devices and retries transient API errors.
* **Multi-format Timestamps**: Handles US‐style and ISO‐8601 timestamp formats.
* **Dry Output**: Dumps full device list to `all_devices.json` for inspection.
* **Stale Detection**: Configurable cutoff in days, defaults to 60.
* **Logging**: Informational and warning logs show progress and any issues.
* **Recycle Bin**: Moves stale devices into the SureMDM Recycle Bin.
* **Permanent Delete**: Force‐delete devices from the Recycle Bin with verification.

---

## 📋 Prerequisites

* Python 3.8+
* A SureMDM account with:

  * API key (`ApiKey` header)
  * Username & password for basic auth
* Access to the SureMDM endpoints:

  * `/api/v2/devicegrid`
  * `/api/v2/device/delete`

---

## 🔧 Installation

1. **Clone this repo**

   ```bash
   git clone https://github.com/yourusername/suremdm-device-cleanup.git
   cd suremdm-device-cleanup
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # on Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration

Create a `.env` file in the project root with:

```ini
API_KEY=your_suremdm_api_key
MY_EMAIL=your_username@example.com
MY_PASSWORD=your_password
FORCE_DELETE_VERIFICATION_CODE=123456   # optional (or you’ll be prompted)
```

* **API\_KEY**: Your SureMDM `ApiKey` header value
* **MY\_EMAIL**: SureMDM login username
* **MY\_PASSWORD**: SureMDM login password
* **FORCE\_DELETE\_VERIFICATION\_CODE**: (Optional) Pre‑set your verification code for permanent delete

---

## 🚀 Usage

Run the script:

```bash
python device_cleanup.py
```

**Steps performed**:

1. Fetches all devices (paged) into `all_devices.json`.
2. Filters devices not seen in the last 60 days (adjustable).
3. Prints a console summary: total stale devices.
4. Saves stale devices to `stale_devices.json` and `stale_devices.csv`.
5. Moves stale devices into the SureMDM Recycle Bin.
6. Prompts (or reads `.env`) for a verification code to `FORCEDELETE_DEVICE` permanently.

### Customizing

* Change `PAGE_LIMIT` or `STALE_DAYS` at the top of the script.
* Modify logging level in `logging.basicConfig()`.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
