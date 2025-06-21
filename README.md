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

## License
MIT 