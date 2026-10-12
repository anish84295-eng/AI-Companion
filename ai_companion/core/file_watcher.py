import os
import threading
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

try:
    from pyflakes.api import check
    from pyflakes.reporter import Reporter
    from io import StringIO
    HAS_PYFLAKES = True
except ImportError:
    HAS_PYFLAKES = False


class FileWatcher(QObject):
    fileChanged = Signal(str)
    errorFound = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._observer = None
        self._watched_paths: set[str] = set()
        self._lock = threading.Lock()

    def startWatching(self, paths: list[str]):
        if self._observer and self._observer.is_alive():
            return
        self._observer = Observer()
        handler = _PyFileHandler(self)
        for p in paths:
            if os.path.isdir(p):
                self._observer.schedule(handler, p, recursive=True)
                self._watched_paths.add(p)
        self._observer.start()

    def stopWatching(self):
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=5)
        self._observer = None
        self._watched_paths.clear()

    def addPath(self, path: str):
        with self._lock:
            if path not in self._watched_paths:
                if os.path.isdir(path):
                    if self._observer and self._observer.is_alive():
                        handler = _PyFileHandler(self)
                        self._observer.schedule(handler, path, recursive=True)
                    self._watched_paths.add(path)

    def runPyflakes(self, filepath: str) -> list[dict]:
        if not HAS_PYFLAKES:
            return []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
            old_stdout = StringIO()
            old_stderr = StringIO()
            reporter = Reporter(old_stdout, old_stderr)
            try:
                check(code, reporter)
            except SyntaxError:
                return [{
                    "file": filepath,
                    "line": 0,
                    "message": "Syntax error in file",
                    "severity": "danger",
                }]
            errors_text = old_stderr.getvalue().strip()
            if not errors_text:
                return []
            results = []
            for line in errors_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    fname = parts[0].strip()
                    try:
                        lineno = int(parts[1].strip())
                    except ValueError:
                        lineno = 0
                    msg = parts[2].strip()
                else:
                    fname = filepath
                    lineno = 0
                    msg = line
                severity = "warning"
                if "imported but unused" in msg:
                    severity = "info"
                elif "undefined name" in msg:
                    severity = "danger"
                results.append({
                    "file": fname,
                    "line": lineno,
                    "message": msg,
                    "severity": severity,
                })
            return results
        except Exception as e:
            return [{"file": filepath, "line": 0, "message": str(e), "severity": "warning"}]

    def checkDirectory(self, dirpath: str) -> list[dict]:
        all_errors = []
        try:
            for root, dirs, files in os.walk(dirpath):
                for fname in files:
                    if fname.endswith(".py"):
                        fpath = os.path.join(root, fname)
                        errors = self.runPyflakes(fpath)
                        all_errors.extend(errors)
        except Exception:
            pass
        return all_errors


class _PyFileHandler(FileSystemEventHandler):
    def __init__(self, watcher: FileWatcher):
        super().__init__()
        self._watcher = watcher

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent):
            self._handle(event.src_path)

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent):
            self._handle(event.src_path)

    def _handle(self, path: str):
        if path.endswith(".py"):
            self._watcher.fileChanged.emit(path)
            errors = self._watcher.runPyflakes(path)
            for err in errors:
                self._watcher.errorFound.emit(err["file"], err["message"])
