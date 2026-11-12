"""Desktop window. The page talks to Python in-process through pywebview's JS bridge: there is
no web server and nothing listens on a port. Files are read from where they are and written only
where the preparer chooses in the Save dialog.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import webview
from webview.dom import DOMEventHandler

from .session import Session

UI_DIR = Path(__file__).resolve().parent / "ui"
FILE_TYPES = ("Passport scans (*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.pdf)", "All files (*.*)")


class Api:
    """Methods callable from the page as ``pywebview.api.<name>(...)``."""

    def __init__(self):
        self.session = Session()
        self.window: webview.Window | None = None

    def state(self):
        return self.session.state()

    def pick_files(self):
        paths = self.window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True, file_types=FILE_TYPES)
        return self.session.add_files(list(paths or []))

    def add_dropped(self, paths):
        return self.session.add_files(list(paths))

    def add_mrz(self, line1, line2):
        return self.session.add_mrz_text(line1, line2)

    def remove(self, sha256):
        return self.session.remove(sha256)

    def set_value(self, key, value):
        return self.session.set_value(key, value)

    def copy_sheet(self):
        """Put the text data sheet on the clipboard."""
        res = self.session.data_sheet("txt")
        if res["ok"]:
            if sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=res["text"].encode(), check=True)
            else:
                return {"ok": False, "error": "Copy is only wired up on macOS so far; use Save."}
        return {k: v for k, v in res.items() if k != "text"}

    def save_sheet(self, fmt):
        fmt = fmt if fmt in ("txt", "json", "csv") else "txt"
        res = self.session.data_sheet(fmt)
        if not res["ok"]:
            return res
        rows = self.session.resolve()
        fam = next((r["value"] for r in rows if r["key"] == "family_name"), "") or "applicant"
        dest = self.window.create_file_dialog(
            webview.FileDialog.SAVE, save_filename=f"{fam.title()}-data-sheet.{fmt}",
            file_types=(f"{fmt.upper()} (*.{fmt})",))
        if not dest:
            return {"ok": False, "error": "cancelled"}
        path = Path(dest if isinstance(dest, str) else dest[0])
        path.write_text(res["text"], encoding="utf-8")
        return {"ok": True, "output": str(path)}

    def reveal(self, path):
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", path], check=False)


def _bind_drop(window: webview.Window, api: Api) -> None:
    def on_drop(event):
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [f["pywebviewFullPath"] for f in files if f.get("pywebviewFullPath")]
        if paths:
            state = api.add_dropped(paths)
            window.evaluate_js(f"window.__render({json.dumps(state)})")

    window.dom.document.events.dragover += DOMEventHandler(lambda e: None, True, True)
    window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)


def main() -> None:
    api = Api()
    api.window = webview.create_window(
        "USCIS Autofill", str(UI_DIR / "index.html"), js_api=api, width=1180, height=860,
        min_size=(900, 640))

    def on_start():
        try:
            _bind_drop(api.window, api)
        except Exception:  # drag-and-drop is a convenience; the Add files button always works
            pass

    webview.start(on_start)


if __name__ == "__main__":
    main()
