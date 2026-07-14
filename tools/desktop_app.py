"""QuantOS Desktop launcher (WP-011, ADR-036).

    python tools/desktop_app.py

Starts the local application server (127.0.0.1:8742) and opens it in a
chromeless Edge app window -- native desktop-app feel, zero Electron.
Closing the terminal stops the server and forgets all broker sessions.
"""

import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

URL = "http://127.0.0.1:8742"


def open_window() -> None:
    time.sleep(1.2)  # let uvicorn bind first
    edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    try:
        subprocess.Popen([edge, f"--app={URL}"])
    except OSError:
        webbrowser.open(URL)  # any default browser still works


def main() -> None:
    threading.Thread(target=open_window, daemon=True).start()
    from api.server import main as serve

    print(f"QuantOS Desktop on {URL}  (Ctrl+C to quit; broker sessions are forgotten on exit)")
    serve()


if __name__ == "__main__":
    main()
