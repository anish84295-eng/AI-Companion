from PySide6.QtCore import QThread, Signal, QObject
from ai_companion.core.screen_capture import ScreenCapture
from ai_companion.core.ocr_engine import OCREngine
from ai_companion.core.config import get_tesseract_path
import re
import threading


class ScreenMonitor(QObject):
    frameCaptured = Signal(object, str)
    errorDetected = Signal(str, str)
    statusChanged = Signal(bool)
    error = Signal(str)

    def __init__(self, interval: float = 5.0, parent=None):
        super().__init__(parent)
        self._capture = ScreenCapture()
        self._ocr = OCREngine(tesseract_path=get_tesseract_path() or None)
        self._interval = interval
        self._running = False
        self._thread: QThread = None

    def startMonitoring(self):
        if self._running:
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self._running = True
        self._thread = QThread()
        self._worker = _MonitorWorker(self._capture, self._ocr, self._interval)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.frameCaptured.connect(self.frameCaptured.emit)
        self._worker.errorDetected.connect(self.errorDetected.emit)
        self._worker.error.connect(self.error.emit)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.start()
        self.statusChanged.emit(True)

    def stopMonitoring(self):
        if not self._running:
            return
        self._running = False
        if self._worker:
            self._worker.stop()
        self.statusChanged.emit(False)

    def isMonitoring(self) -> bool:
        return self._running

    def _on_worker_finished(self):
        self._running = False
        self.statusChanged.emit(False)

    def setInterval(self, interval: float):
        self._interval = interval
        if self._worker:
            self._worker._interval = interval


_ERR_TOKEN_EXCLUDED = {"genericerror", "error", "exception"}
_ERR_LINE_START = re.compile(
    r'^\s*([A-Za-z_]\w*(?:Error|Exception))\b\s*(?::|[\u2014\u2013\u2015-]|\s*$)'
)
_ERR_INLINE = re.compile(r'\b([A-Za-z_]\w*(?:Error|Exception))\b\s*[:：]')
_ERR_TRACE = re.compile(
    r'(?i)traceback|exception in thread|\.java:|compilation error|linker error|'
    r'fatal error|segmentation fault|core dumped|kernel panic|\berrno\b|'
    r'Uncaught (?:Error|TypeError)|Cannot read property|is not a function|'
    r'undefined is not|null pointer|\berror\s*:|\bFile\b[^\n]*\blines?\s+\d+'
)


class _MonitorWorker(QObject):
    frameCaptured = Signal(object, str)
    errorDetected = Signal(str, str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, capture: ScreenCapture, ocr: OCREngine, interval: float):
        super().__init__()
        self._capture = capture
        self._ocr = ocr
        self._interval = interval
        self._stop_event = threading.Event()
        self._should_stop = False

    def run(self):
        while not self._stop_event.is_set():
            try:
                img = self._capture.captureScreenIfChanged()
                if img is not None:
                    text = self._ocr.extractText(img)
                    if text:
                        self.frameCaptured.emit(img, text)
                        error_lines = self._detect_errors_in_text(text)
                        if error_lines:
                            self.errorDetected.emit(text, "\n".join(error_lines))
            except Exception as e:
                self.error.emit(str(e))
            if self._stop_event.wait(self._interval):
                break
        self.finished.emit()

    def stop(self):
        self._should_stop = True
        self._stop_event.set()

    def _is_probable_error_line(self, line: str) -> bool:
        if _ERR_TRACE.search(line):
            return True
        m = _ERR_LINE_START.match(line)
        if m and m.group(1).lower() not in _ERR_TOKEN_EXCLUDED:
            return True
        for t in _ERR_INLINE.finditer(line):
            if t.group(1).lower() not in _ERR_TOKEN_EXCLUDED:
                return True
        return False

    def _detect_errors_in_text(self, text: str) -> list[str]:
        lines = text.split("\n")
        error_lines = []
        for line in lines:
            s = line.strip()
            if s and self._is_probable_error_line(s):
                error_lines.append(s)
        return error_lines
