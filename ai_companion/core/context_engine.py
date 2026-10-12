from typing import Optional


class ContextEngine:
    def __init__(self):
        self._context_parts: list[str] = []
        self._ocr_text: str = ""
        self._error_info: str = ""
        self._file_context: str = ""
        self._memory_context: str = ""

    def buildContext(self, ocr_text: str = "", error_info: str = "",
                     file_context: str = "", memory_context: str = "",
                     user_query: str = "") -> str:
        parts = []
        if memory_context:
            parts.append(f"[Memory]\n{memory_context}")
        if error_info:
            parts.append(f"[Detected Error]\n{error_info}")
        if ocr_text:
            ocr_trimmed = ocr_text[:3000]
            parts.append(f"[Screen OCR Text]\n{ocr_trimmed}")
        if file_context:
            parts.append(f"[File Context]\n{file_context}")
        if user_query:
            parts.append(f"[User Query]\n{user_query}")
        return "\n\n".join(parts) if parts else "No context available."

    def combineContext(self, *contexts: str) -> str:
        non_empty = [c for c in contexts if c.strip()]
        return "\n\n---\n\n".join(non_empty) if non_empty else ""

    def setOCRText(self, text: str):
        self._ocr_text = text

    def setErrorInfo(self, info: str):
        self._error_info = info

    def setFileContext(self, context: str):
        self._file_context = context

    def setMemoryContext(self, context: str):
        self._memory_context = context

    def getFullContext(self) -> str:
        return self.buildContext(
            ocr_text=self._ocr_text,
            error_info=self._error_info,
            file_context=self._file_context,
            memory_context=self._memory_context,
        )

    def clear(self):
        self._context_parts.clear()
        self._ocr_text = ""
        self._error_info = ""
        self._file_context = ""
        self._memory_context = ""

    def buildErrorMessage(self, error_info: dict) -> str:
        parts = []
        if error_info.get("error_type"):
            parts.append(f"Error Type: {error_info['error_type']}")
        if error_info.get("error_message"):
            parts.append(f"Message: {error_info['error_message']}")
        if error_info.get("file_name"):
            parts.append(f"File: {error_info['file_name']}")
        if error_info.get("line_number"):
            parts.append(f"Line: {error_info['line_number']}")
        if error_info.get("language"):
            parts.append(f"Language: {error_info['language']}")
        if error_info.get("error_line"):
            parts.append(f"Code: {error_info['error_line']}")
        return "\n".join(parts)
