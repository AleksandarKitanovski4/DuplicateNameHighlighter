# Duplicate Name Highlighter

A real-time desktop utility to highlight duplicate names in any application window using OCR and a transparent overlay.

## Features
- Region selection & screen capture
- Change detection (pHash) to minimize OCR
- Fast OCR with Tesseract
- Duplicate tracking (in-memory + SQLite)
- Overlay visualization (color-coded markers)
- Scroll tracking & marker repositioning
- Configurable settings (interval, threshold, whitelist, etc.)
- CSV export
- Logging & diagnostics

## Installation

### 1. Pip (Developer Mode)
```bash
pip install -r requirements.txt
python main.py
```

### 2. Standalone Executable (Windows/macOS)
- Install [PyInstaller](https://pyinstaller.org/):
  ```bash
  pip install pyinstaller
  ```
- Build the app:
  ```bash
  pyinstaller duplicate_name_highlighter.spec
  ```
- The executable will be in the `dist/DuplicateNameHighlighter` folder.

## Usage
- Run the app and select a region to monitor.
- Use the main window to start/stop scanning, export CSV, or adjust settings.
- Duplicates are highlighted with color-coded markers (orange/red).
- All actions are logged to `duplicate_highlighter.log`.

## Notes
- Requires Tesseract OCR installed and in your PATH.
- Works on Windows 10/11 and macOS (PyQt5, PyInstaller supported).
- For best results, use high-contrast regions and adjust OCR whitelist/settings.

## Scroll Tracking

DuplicateNameHighlighter now supports automatic scroll tracking for dynamic content (e.g., browser, Excel, Freshdesk). When enabled, the app detects when the target window is scrolled vertically and automatically repositions overlay markers to follow the visible content. This ensures that duplicate name highlights remain accurate even as you scroll.

**How to enable/configure:**
- Scroll tracking is enabled by default.
- You can adjust the scroll detection threshold in the Settings dialog under the "General" tab ("Scroll Detection Threshold").
- The threshold controls how sensitive the app is to vertical movement; lower values detect smaller scrolls.
- Markers will shift up or down as you scroll, and only new/unseen content is rescanned for duplicates.

**Tips:**
- For best results, use a region that covers only the scrollable area.
- False positives are minimized by comparing OCR bounding boxes and image strips.

## CSV Export

You can export all detected names and their statistics to a CSV file for further analysis or reporting.

**How to export:**
- Open the Settings dialog and go to the "Export" tab.
- Click the "Export CSV" button.
- Choose a destination folder when prompted.
- After export, a message will confirm the location of the file (e.g., `C:/Users/YourName/Documents/duplicate_names.csv`).

**Sample output path:**
```
C:/Users/YourName/Documents/duplicate_names.csv
```

The CSV includes columns: Name, First Seen, Last Seen, Total Occurrences.

## License
MIT 