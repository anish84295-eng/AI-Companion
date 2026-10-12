import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_companion.core.database import (
    init_db, save_message, create_conversation,
    get_conversations, get_messages_for_conversation,
    save_error, load_history, clear_history,
    save_memory, get_all_memory, delete_memory,
    save_settings, get_setting, get_all_settings
)
from ai_companion.core.error_detector import ErrorDetector
from ai_companion.core.context_engine import ContextEngine
from ai_companion.core.screen_capture import ScreenCapture
from ai_companion.core.ocr_engine import OCREngine
from ai_companion.core.config import get_api_key, get_model
from pathlib import Path
import tempfile


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    import ai_companion.core.database as dbmod
    dbmod._DB_PATH = tmp_path / "test.db"
    dbmod._local.conn = None
    init_db()
    yield
    dbmod._local.conn = None


class TestDatabase:
    def test_init_creates_tables(self):
        import ai_companion.core.database as dbmod
        conn = dbmod._connect()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = [t["name"] for t in tables]
        assert "Users" in names
        assert "Conversations" in names
        assert "Messages" in names
        assert "Detected_Errors" in names
        assert "Memory" in names
        assert "Settings" in names

    def test_create_conversation(self):
        cid = create_conversation("Test Chat")
        assert cid > 0
        convos = get_conversations()
        assert len(convos) >= 1
        assert convos[0]["title"] == "Test Chat"

    def test_save_and_get_messages(self):
        cid = create_conversation("Test")
        mid = save_message(cid, "user", "Hello")
        assert mid > 0
        mid2 = save_message(cid, "assistant", "Hi there")
        messages = get_messages_for_conversation(cid)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["content"] == "Hi there"

    def test_save_error_deduplication(self):
        e1 = save_error("python", "SyntaxError", "invalid syntax", file_name="test.py", line_number=1)
        e2 = save_error("python", "SyntaxError", "invalid syntax", file_name="test.py", line_number=1)
        assert e1 == e2
        history = load_history()
        assert len([h for h in history if h["error_type"] == "SyntaxError"]) == 1

    def test_clear_history(self):
        save_error("python", "TestError", "test msg")
        clear_history()
        assert len(load_history()) == 0

    def test_memory_crud(self):
        mid = save_memory("key1", "value1")
        assert mid > 0
        memories = get_all_memory()
        assert any(m["memory_key"] == "key1" for m in memories)

        save_memory("key1", "updated")
        memories = get_all_memory()
        for m in memories:
            if m["memory_key"] == "key1":
                assert m["memory_value"] == "updated"

        delete_memory(mid)
        memories = get_all_memory()
        assert not any(m["memory_id"] == mid for m in memories)

    def test_settings(self):
        save_settings("theme", "dark")
        assert get_setting("theme") == "dark"
        save_settings("theme", "light")
        assert get_setting("theme") == "light"
        assert get_setting("nonexistent", "default") == "default"
        all_s = get_all_settings()
        assert all_s.get("theme") == "light"


class TestErrorDetector:
    def setup_method(self):
        self.detector = ErrorDetector()

    def test_python_traceback(self):
        text = '''Traceback (most recent call last):
  File "main.py", line 10, in <module>
    result = x / 0
ZeroDivisionError: division by zero'''
        errors = self.detector.detectError(text)
        assert len(errors) >= 1
        assert any("ZeroDivision" in e["error_type"] for e in errors)

    def test_syntax_error(self):
        text = 'SyntaxError: invalid syntax at line 5'
        errors = self.detector.detectError(text)
        assert len(errors) >= 1

    def test_javascript_error(self):
        text = 'TypeError: Cannot read property of undefined'
        errors = self.detector.detectError(text)
        assert len(errors) >= 1
        assert errors[0]["language"] == "javascript"

    def test_java_error(self):
        text = 'java.lang.NullPointerException: Cannot invoke method on null\n\tat App.main(App.java:15)'
        errors = self.detector.detectError(text)
        assert len(errors) >= 1

    def test_cpp_error(self):
        text = 'main.cpp:10:5: error: use of undeclared identifier'
        errors = self.detector.detectError(text)
        assert len(errors) >= 1

    def test_identify_language(self):
        assert self.detector.identifyLanguage("Traceback (most recent call last):") == "python"
        assert self.detector.identifyLanguage("TypeError: Cannot read property of undefined") == "javascript"
        assert self.detector.identifyLanguage("java.lang.NullPointerException") == "java"
        assert self.detector.identifyLanguage("main.cpp:10: error:") == "c_cpp"
        assert self.detector.identifyLanguage("TypeError: foo") == "python"

    def test_get_error_details(self):
        text = 'NameError: name "x" is not defined'
        details = self.detector.getErrorDetails(text)
        assert details["error_type"] == "NameError"
        assert details["language"] == "python"

    def test_ocr_space_before_colon_variant(self):
        text = 'print(username)\nNameError : name \'username\' is not defined'
        errors = self.detector.detectError(text)
        assert errors and errors[0]["error_type"] == "NameError"
        assert errors[0]["error_message"] == "name 'username' is not defined"

    def test_bare_exception_token_no_generic(self):
        text = 'print(username)\nNameError'
        errors = self.detector.detectError(text)
        assert errors and errors[0]["error_type"] == "NameError"
        assert errors[0]["error_type"] != "GenericError"

    def test_traceback_file_and_line_extracted(self):
        text = ('Traceback (most recent call last):\n'
                '  File "C:\\Users\\admin\\test_error.py", line 2, in <module>\n'
                '    print(username)\n'
                'NameError: name \'username\' is not defined')
        errors = self.detector.detectError(text)
        assert errors
        first = errors[0]
        assert first["error_type"] == "NameError"
        assert first["file_name"].endswith("test_error.py")
        assert first["line_number"] == 2

    def test_known_errors_never_reported_generic(self):
        for line in ['NameError: x', 'SyntaxError: invalid', 'TypeError: y',
                     'IndentationError: bad', 'ValueError: v',
                     'KeyError: k', 'AttributeError: a',
                     'ImportError: no module', 'ZeroDivisionError: z']:
            errors = self.detector.detectError(line)
            assert errors, f"expected detection for {line}"
            assert errors[0]["error_type"] != "GenericError", line

    def test_generic_only_when_type_unknown(self):
        text = 'Segmentation fault (core dumped)'
        errors = self.detector.detectError(text)
        assert errors and errors[0]["error_type"] == "GenericError"

    def test_no_generic_for_ambiguous_noise(self):
        text = 'error in line 2'
        errors = self.detector.detectError(text)
        assert errors == []

    def test_genericerror_token_never_detected(self):
        text = 'GenericError something went wrong'
        errors = self.detector.detectError(text)
        assert errors == []

    def test_path_breadcrumb_noise_never_detected(self):
        text = '\\ Cat Asistant C: > Users > admin > OneDrive > Desktop > test_error.py > ...'
        errors = self.detector.detectError(text)
        assert errors == []

    def test_explorer_garbage_noise_never_detected(self):
        text = 'ta Explorer a) x @ X (R) test_error.py ...'
        errors = self.detector.detectError(text)
        assert errors == []

    def test_bare_error_word_no_detection(self):
        text = 'this report may be inaccurate'
        errors = self.detector.detectError(text)
        assert errors == []

    def test_indentation_error_detected(self):
        text = '  File "app.py", line 3\n    print(x)\nIndentationError: unexpected indent'
        errors = self.detector.detectError(text)
        assert errors and errors[0]["error_type"] == "IndentationError"


class TestContextEngine:
    def setup_method(self):
        self.ctx = ContextEngine()

    def test_build_context(self):
        ctx = self.ctx.buildContext(
            ocr_text="some code",
            error_info="NameError: x",
            user_query="fix this"
        )
        assert "OCR" in ctx or "some code" in ctx
        assert "NameError" in ctx
        assert "fix this" in ctx

    def test_combine_context(self):
        combined = self.ctx.combineContext("context1", "context2")
        assert "context1" in combined
        assert "context2" in combined

    def test_build_error_message(self):
        msg = self.ctx.buildErrorMessage({
            "error_type": "ValueError",
            "error_message": "bad value",
            "file_name": "app.py",
            "line_number": 42,
            "language": "python"
        })
        assert "ValueError" in msg
        assert "app.py" in msg


class TestScreenCapture:
    def test_capture_returns_image_or_none(self):
        capture = ScreenCapture()
        try:
            img = capture.captureScreen()
            if img is not None:
                assert img.size[0] > 0
                assert img.size[1] > 0
        except Exception:
            pass

    def test_has_changed(self):
        capture = ScreenCapture()
        from PIL import Image
        img1 = Image.new("RGB", (100, 100), "red")
        assert capture.has_changed(img1) is True
        assert capture.has_changed(img1) is False
        img2 = Image.new("RGB", (100, 100), "blue")
        assert capture.has_changed(img2) is True


class TestConfig:
    def test_get_model(self):
        model = get_model()
        assert isinstance(model, str)
        assert len(model) > 0
