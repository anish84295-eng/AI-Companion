import re
from typing import Optional


class ErrorDetector:
    def detectError(self, text: str) -> list[dict]:
        errors = []
        is_js_context = any(k in text for k in [
            "Cannot read property", "is not a function",
            "undefined is not", "Uncaught ", "at Object.",
        ])
        is_java_context = any(k in text for k in [
            "Exception in thread", ".java:", "java.lang.", "at com.", "at org.", "at java."
        ])
        if not is_js_context and not is_java_context:
            errors.extend(self._parse_python_traceback(text))
        if is_js_context:
            errors.extend(self._parse_js_errors(text))
        if is_java_context:
            errors.extend(self._parse_java_errors(text))
        if not errors:
            errors.extend(self._parse_cpp_errors(text))
        if not errors:
            errors.extend(self._scan_known_types(text))
        if not errors:
            errors.extend(self._parse_generic_errors(text))
        return errors

    def identifyLanguage(self, text: str) -> str:
        if "Traceback (most recent call last)" in text:
            return "python"
        if any(k in text for k in [
            "Cannot read property", "is not a function",
            "undefined is not", "Uncaught TypeError",
            "Uncaught Reference", "Uncaught Syntax",
        ]):
            return "javascript"
        if any(k in text for k in ["Exception in thread", ".java:", "java.lang.", "at com.", "at org."]):
            return "java"
        if any(k in text for k in ["error:", "warning:", "fatal:"]) and ":" in text:
            return "c_cpp"
        py_errors = ["SyntaxError", "IndentationError", "NameError", "TypeError",
                      "ValueError", "KeyError", "IndexError", "AttributeError",
                      "ImportError", "ModuleNotFoundError", "ZeroDivisionError",
                      "FileNotFoundError", "UnicodeDecodeError", "RecursionError"]
        for pe in py_errors:
            if pe in text:
                return "python"
        return "unknown"

    def getErrorDetails(self, text: str) -> dict:
        lang = self.identifyLanguage(text)
        errors = self.detectError(text)
        if errors:
            err = errors[0]
            if lang == "unknown" and err.get("language", "unknown") != "unknown":
                lang = err["language"]
            return {**err, "language": lang}
        return {
            "language": lang,
            "error_type": "Unknown",
            "error_message": text[:200] if text else "",
            "file_name": "",
            "line_number": 0,
            "severity": "info",
        }

    def _parse_python_traceback(self, text: str) -> list[dict]:
        errors = []
        lines = text.split("\n")
        file_re = re.compile(
            r'File\s*:?\s*"?([^"\r\n]+)"?\s*,?\s*line\s*:?\s*(\d+)'
        )
        exc_re = re.compile(
            r'^\s*((?:(?:[A-Za-z_]\w*|[\u3000-\u303f\u4e00-\u9fff])\s*\.\s*)*'
            r'[A-Za-z_]\w*(?:Error|Exception))'
            r'\s*(?::|[\u2014\u2013\u2015-])?\s*(.*)$'
        )

        def _nearest_file(i: int):
            for j in range(i - 1, max(-1, i - 8), -1):
                fm = file_re.search(lines[j])
                if fm:
                    return fm.group(1), int(fm.group(2))
            return "", 0

        for i, line in enumerate(lines):
            m = exc_re.match(line)
            if not m:
                continue
            error_type = m.group(1).strip()
            if error_type.lower() in ("genericerror", "error", "exception"):
                continue
            error_message = m.group(2).strip()
            if error_message.lower() in ("most recent call last",):
                continue
            file_name, line_number = _nearest_file(i)
            severity = self._classify_severity(error_type, "python")
            errors.append({
                "error_type": error_type,
                "error_message": error_message,
                "file_name": file_name,
                "line_number": line_number,
                "error_line": "",
                "severity": severity,
                "language": "python",
            })
        return errors

    def _scan_known_types(self, text: str) -> list[dict]:
        errors = []
        lines = text.split("\n")
        file_re = re.compile(
            r'File\s*:?\s*"?([^"\r\n]+)"?\s*,?\s*line\s*:?\s*(\d+)'
        )
        excluded = {"genericerror", "error", "exception"}
        line_start_re = re.compile(
            r'^\s*([A-Za-z_]\w*(?:Error|Exception))\b\s*(?::|[\u2014\u2013\u2015-]|\s*$)'
        )
        inline_re = re.compile(r'\b([A-Za-z_]\w*(?:Error|Exception))\b\s*[:：]')
        seen_lines = set()
        for i, line in enumerate(lines):
            m = line_start_re.match(line) or inline_re.search(line)
            if not m:
                continue
            error_type = m.group(1)
            if error_type.lower() in excluded:
                continue
            if i in seen_lines:
                continue
            seen_lines.add(i)
            rest = lines[i][m.end():]
            error_message = re.sub(r'^\s*(?::|[\u2014\u2013\u2015-])?\s*', '', rest).strip()
            file_name, line_number = "", 0
            for j in range(i - 1, max(-1, i - 8), -1):
                fm = file_re.search(lines[j])
                if fm:
                    file_name = fm.group(1)
                    line_number = int(fm.group(2))
                    break
            lang = self.identifyLanguage(text)
            if lang == "unknown":
                lang = "python"
            errors.append({
                "error_type": error_type,
                "error_message": error_message,
                "file_name": file_name,
                "line_number": line_number,
                "error_line": "",
                "severity": self._classify_severity(error_type, lang),
                "language": lang,
            })
        return errors

    def _parse_js_errors(self, text: str) -> list[dict]:
        errors = []
        patterns = [
            re.compile(r'(TypeError|ReferenceError|SyntaxError|RangeError|Error):\s*(.+?)(?:\n|$)'),
            re.compile(r'Uncaught\s+(TypeError|ReferenceError|SyntaxError|RangeError|Error):\s*(.+?)(?:\n|$)'),
            re.compile(r'at\s+(?:.*?\s+\()?([^():]+):(\d+):\d+\)?'),
        ]
        for m in patterns[0].finditer(text):
            severity = self._classify_severity(m.group(1), "javascript")
            errors.append({
                "error_type": m.group(1),
                "error_message": m.group(2).strip(),
                "file_name": "",
                "line_number": 0,
                "error_line": "",
                "severity": severity,
                "language": "javascript",
            })
        for m in patterns[1].finditer(text):
            errors.append({
                "error_type": m.group(1),
                "error_message": m.group(2).strip(),
                "file_name": "",
                "line_number": 0,
                "error_line": "",
                "severity": "critical",
                "language": "javascript",
            })
        if not errors:
            for m in patterns[2].finditer(text):
                errors.append({
                    "error_type": "RuntimeError",
                    "error_message": m.group(0),
                    "file_name": m.group(1),
                    "line_number": int(m.group(2)),
                    "error_line": "",
                    "severity": "warning",
                    "language": "javascript",
                })
        return errors

    def _parse_java_errors(self, text: str) -> list[dict]:
        errors = []
        pattern = re.compile(
            r'((?:\w+\.)*\w+(?:Exception|Error))[\s:]+(.+?)(?:\n|$)'
        )
        file_pattern = re.compile(r'at\s+[\w.$]+\(([^)]+):(\d+)\)')
        for m in pattern.finditer(text):
            severity = self._classify_severity(m.group(1).split(".")[-1], "java")
            errors.append({
                "error_type": m.group(1).split(".")[-1],
                "error_message": m.group(2).strip(),
                "file_name": "",
                "line_number": 0,
                "error_line": "",
                "severity": severity,
                "language": "java",
            })
        for m in file_pattern.finditer(text):
            fname = m.group(1)
            if errors and not errors[-1]["file_name"]:
                errors[-1]["file_name"] = fname
                errors[-1]["line_number"] = int(m.group(2))
        return errors

    def _parse_cpp_errors(self, text: str) -> list[dict]:
        errors = []
        gcc_pattern = re.compile(r'([^:]+):(\d+):\d+:\s*(error|warning|fatal error):\s*(.+)')
        msvc_pattern = re.compile(r'([^:(]+)\((\d+)(?:,\d+)?:\s*(error|warning)\s+\w+:\s*(.+)')
        for m in gcc_pattern.finditer(text):
            severity = "critical" if m.group(3) == "fatal error" else m.group(3)
            errors.append({
                "error_type": m.group(3).title(),
                "error_message": m.group(4).strip(),
                "file_name": m.group(1),
                "line_number": int(m.group(2)),
                "error_line": "",
                "severity": severity,
                "language": "c_cpp",
            })
        for m in msvc_pattern.finditer(text):
            errors.append({
                "error_type": m.group(3).title(),
                "error_message": m.group(4).strip(),
                "file_name": m.group(1),
                "line_number": int(m.group(2)),
                "error_line": "",
                "severity": m.group(3),
                "language": "c_cpp",
            })
        return errors

    def _parse_generic_errors(self, text: str) -> list[dict]:
        errors = []
        if re.search(r'\b[A-Za-z_]\w*(?:Error|Exception)\b', text):
            return errors
        patterns = [
            (r'(?i)\bfatal\s+(?:error|exception)\b', "critical"),
            (r'(?i)\bsegmentation\s+fault\b', "critical"),
            (r'(?i)\bcore dumped\b', "critical"),
            (r'(?i)\bkernel panic\b', "critical"),
            (r'(?i)\bgeneral\s+protection\s+fault\b', "critical"),
            (r'(?i)\berrno\s*\(?\s*-?\s*\d+', "warning"),
        ]
        for pat, sev in patterns:
            for m in re.finditer(pat, text):
                errors.append({
                    "error_type": "GenericError",
                    "error_message": m.group(0).strip(),
                    "file_name": "",
                    "line_number": 0,
                    "error_line": "",
                    "severity": sev,
                    "language": "unknown",
                })
        return errors

    def _classify_severity(self, error_type: str, language: str) -> str:
        critical_keywords = ["fatal", "panic", "segmentation", "out of memory", "stackoverflow"]
        warning_keywords = ["deprecat", "warning", "lint"]
        error_type_lower = error_type.lower()
        for kw in critical_keywords:
            if kw in error_type_lower:
                return "critical"
        for kw in warning_keywords:
            if kw in error_type_lower:
                return "warning"
        if "Error" in error_type:
            return "danger"
        return "info"
