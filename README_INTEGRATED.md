# Duplicate Name Highlighter

A Windows desktop application that continuously scans a user-defined screen region for names, detects duplicate entries in real time, and highlights them with a transparent overlay.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [Modules](#modules)
7. [Troubleshooting](#troubleshooting)
8. [License](#license)

---

## Features

* **Real-time duplicate detection** using OCR (Tesseract).
* **Transparent overlay** with semi-transparent markers over repeated names.
* **Auto-scan** with configurable interval and change detection (pHash).
* **Session & Database tracking**: in-memory session reset and persistent SQLite storage.
* **Minimal GUI**: toggle auto-scan, set interval, select region, reset session, clear database.

---

## Architecture

```plaintext
+----------------+         +-----------------+       +-------------+
| ScreenCapture  |--images |   OCRProcessor  |--texts| Duplicate   |
|                |         |  (Tesseract)    |       | Tracker     |--+---> Overlay
|  (capture +    |         +-----------------+       +-------------+  |
|   change-detect)                                                    |
+--------+-------+                                                    |
         |                                                           |
         |   stats                                                   |
         +-----------------------------------------------------------+
                                   |
                                   v
                             NameDatabase (SQLite)
```

---

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/AleksandarKitanovski4/DuplicateNameHighlighter.git
   cd DuplicateNameHighlighter
   ```
2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```
3. **Install Tesseract OCR** (offline):

   * Windows: Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
   * Ensure `tesseract.exe` path is set in code or in PATH.

---

## Usage

```bash
python example_usage.py
```

* **Select Region**: Draw area to monitor.
* **Enable Auto-Scan**: Scans every N seconds.
* **Reset Session**: Clears current session memory.
* **Clear Database**: Erases persistent data.

---

## Configuration

Settings are saved in `settings.json`:

```json
{
  "region": [x, y, width, height],
  "auto_scan": true,
  "interval": 3
}
```

Adjust:

* `auto_scan`: `true` or `false`
* `interval`: seconds between scans
* `region`: monitored screen area

---

## Modules

* **core/screen\_capture.py**: capture, change detection, OCR integration.
* **core/duplicate\_tracker.py**: in-memory and DB tracking + overlay calls.
* **core/ocr\_processor.py**: OpenCV preprocessing & Tesseract OCR.
* **gui/overlay.py**: PyQt transparent overlay window.
* **gui/main\_window\.py**: Minimal settings GUI.
* **utils/database.py**: SQLite persistence and stats.

---

## Troubleshooting

* **TesseractNotFoundError**: Check `tesseract_cmd` path.
* **Overlay not clickable**: Ensure click-through attributes set.
* **Slow OCR**: Increase `interval` or refine change threshold.
* **False duplicates**: Adjust `hash_threshold` or implement scroll filtering.

Enable debug logs:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## License

This project is provided for educational and development use.
