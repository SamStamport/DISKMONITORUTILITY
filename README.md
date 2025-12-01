# Disk Monitor Utility

A simple Windows utility to identify which processes are hogging your disk. Features a GUI interface and command-line usage.

## Quick Start

### Using the GUI (Recommended)

Simply run the pre-built Windows executable:

```powershell
.\dist\DiskMonitor.exe
```

**Features:**
- Start/Stop disk monitoring
- Adjust duration, interval, and top N processes to display
- Export results to JSON
- Real-time table showing PID, process name, read/write MB, and total IO

### Python Scripts

**GUI (Tkinter-based, cross-platform):**
```powershell
python disk_monitor_gui.py
```

**CLI (original, simple script):**
```powershell
python disk_monitor.py
```

## Installation & Setup

### From Source (Python 3.13+)

1. Clone the repository:
```powershell
git clone https://github.com/SamStamport/DISKMONITORUTILITY.git
cd DISKMONITORUTILITY
```

2. Create a virtual environment and install dependencies:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Run the GUI or CLI:
```powershell
python disk_monitor_gui.py
# or
python disk_monitor.py
```

### Building Your Own .exe

If you want to rebuild the executable:

```powershell
# Activate venv (if not already)
.\.venv\Scripts\Activate.ps1

# Install PyInstaller
pip install pyinstaller

# Build the .exe
pyinstaller --onefile --noconsole --name DiskMonitor disk_monitor_gui.py

# The exe will be in .\dist\DiskMonitor.exe
```

## How It Works

- **disk_monitor_gui.py**: Tkinter GUI that samples disk I/O per process at regular intervals, computes deltas (not cumulative), and displays results in a sortable table.
- **disk_monitor.py**: Original CLI script for headless monitoring.
- Uses `psutil` to read process I/O counters and compute per-interval byte transfers.

## Pitfalls & Troubleshooting

### Issue: "No module named psutil"
- **Fix:** Ensure psutil is installed: `pip install psutil` (or in the venv: `pip install -r requirements.txt`)

### Issue: Permission errors on certain processes
- **Fix:** Some system processes require Administrator privileges. The tool skips inaccessible processes; run as Administrator if you need to include them.

### Issue: .exe fails to start
- **Fix:** Run from PowerShell to see errors: `.\dist\DiskMonitor.exe` (or check antivirus/SmartScreen warnings)

### Issue: Antivirus flags the .exe
- **Fix:** This is normal for newly-built executables. Whitelist in your AV settings or sign the executable (optional).

### Issue: GUI window is slow to appear
- **Fix:** Single-file .exe extracts at startup (using `--onefile`). This is normal on first run; subsequent runs are faster.

## Development Notes

- **Python Version:** Built and tested with Python 3.13.7 (compatible with 3.12+)
- **Tkinter:** Built-in on Windows Python; no extra installation needed
- **Threading:** GUI uses background worker thread + queue for thread-safe updates
- **I/O Deltas:** Per-interval deltas prevent double-counting across samples
- **PyInstaller:** Version 6.17.0 used for exe packaging

## License

MIT (use freely)

## Repository

GitHub: https://github.com/SamStamport/DISKMONITORUTILITY
