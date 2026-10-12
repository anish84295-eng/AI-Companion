from PySide6.QtCore import QObject, Signal, QThread
from openai import OpenAI
from ai_companion.core.config import get_api_key, get_model, get_base_url
from ai_companion.core.database import get_setting
from typing import Optional
import json


class AIRequestThread(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
            self.succeeded.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


def _skill_guidance(level: str = "") -> str:
    level = (level or get_setting("skill_level", "intermediate")).lower().strip()
    if level == "beginner":
        return (
            "The user is a beginner. Explain in simple, non-technical language. "
            "Avoid jargon and define any necessary terms. Give clear step-by-step "
            "instructions and always show the corrected code."
        )
    if level == "advanced":
        return (
            "The user is an advanced developer. Assume deep technical expertise. "
            "Be precise and detailed, use standard technical terminology directly, "
            "and focus on the root cause and best-practice fixes without over-explaining basics."
        )
    return (
        "The user has an intermediate skill level. Explain clearly with a short "
        "Explanation, Cause, Fix, and Corrected Code, briefly defining any uncommon terms."
    )


class AIEngine(QObject):
    responseReady = Signal(str)
    streamChunk = Signal(str)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client: Optional[OpenAI] = None
        self._model = get_model()
        self._request_threads = set()
        self._init_client()

    def _init_client(self):
        api_key = get_api_key()
        base_url = get_base_url()
        if not api_key:
            self._client = None
            return
        kwargs = {"api_key": api_key, "base_url": base_url, "timeout": 45.0, "max_retries": 0}
        try:
            self._client = OpenAI(**kwargs)
        except Exception as e:
            self._client = None
            self.error.emit(f"Failed to initialize AI client: {e}")

    def refresh_client(self):
        self._model = get_model()
        self._init_client()

    def isConnected(self) -> bool:
        return self._client is not None

    def _build_messages(self, prompt: str, context: str = "",
                        system_prompt: str = "", history: list[dict] = None) -> list[dict]:
        guidance = _skill_guidance()
        if system_prompt:
            system_prompt = f"{system_prompt}\n\n{guidance}"
        else:
            system_prompt = (
                "You are AI-Companion, a helpful coding assistant. "
                "When explaining errors, provide:\n"
                "1. **Explanation**: What the error means\n"
                "2. **Cause**: Why it happened\n"
                "3. **Fix**: How to fix it\n"
                "4. **Corrected Code**: The fixed code if applicable\n\n"
                "Be concise, clear, and helpful. Use markdown for code blocks.\n\n"
                f"{guidance}"
            )
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-20:])
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"
        messages.append({"role": "user", "content": full_prompt})
        return messages

    def askAI(self, prompt: str, context: str = "",
              system_prompt: str = "", history: list[dict] = None) -> str:
        if not self._client:
            return "AI client not configured. Please set OPENROUTER_API_KEY in .env"
        try:
            messages = self._build_messages(prompt, context, system_prompt, history)
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=4096,
                temperature=0.7,
            )
            text = response.choices[0].message.content
            self.responseReady.emit(text)
            return text
        except Exception as e:
            err = f"AI request failed: {e}"
            self.error.emit(err)
            return err

    def askAIAsync(self, prompt: str, context: str = "",
                   system_prompt: str = "", history: list[dict] = None,
                   on_success=None, on_error=None):
        if not self._client:
            self.responseReady.emit("AI client not configured. Please set OPENROUTER_API_KEY in .env")
            return None
        try:
            messages = self._build_messages(prompt, context, system_prompt, history)
        except Exception as e:
            self.error.emit(f"AI request failed: {e}")
            if on_error:
                on_error(f"AI request failed: {e}")
            return None

        def _do():
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=4096,
                temperature=0.7,
            )
            return response.choices[0].message.content

        def _done(text):
            self.responseReady.emit(text)
            if on_success:
                on_success(text)

        def _fail(msg):
            self.error.emit(f"AI request failed: {msg}")
            if on_error:
                on_error(f"AI request failed: {msg}")

        thread = AIRequestThread(_do)
        thread.succeeded.connect(_done)
        thread.failed.connect(_fail)
        thread.finished.connect(lambda: self._request_threads.discard(thread))
        self._request_threads.add(thread)
        thread.start()
        return thread

    def explainCode(self, code: str, language: str = "",
                    context: str = "") -> str:
        prompt = f"Explain the following {language} code:\n\n```{language}\n{code}\n```"
        if context:
            prompt = f"Context: {context}\n\n{prompt}"
        return self.askAI(prompt)

    def analyzeError(self, error_info: dict, ocr_text: str = "",
                     file_context: str = "") -> str:
        prompt_parts = ["Analyze this error and provide Explanation, Cause, Fix, and Corrected Code:"]
        for key in ["error_type", "error_message", "file_name", "line_number", "language", "error_line"]:
            if error_info.get(key):
                prompt_parts.append(f"- {key}: {error_info[key]}")
        if ocr_text:
            prompt_parts.append(f"\nScreen OCR text:\n{ocr_text[:2000]}")
        if file_context:
            prompt_parts.append(f"\nFile context:\n{file_context[:2000]}")
        return self.askAI("\n".join(prompt_parts))

    def analyzeErrorAsync(self, error_info: dict, ocr_text: str = "",
                          file_context: str = "", on_success=None, on_error=None):
        prompt_parts = ["Analyze this error and provide Explanation, Cause, Fix, and Corrected Code:"]
        for key in ["error_type", "error_message", "file_name", "line_number", "language", "error_line"]:
            if error_info.get(key):
                prompt_parts.append(f"- {key}: {error_info[key]}")
        if ocr_text:
            prompt_parts.append(f"\nScreen OCR text:\n{ocr_text[:2000]}")
        if file_context:
            prompt_parts.append(f"\nFile context:\n{file_context[:2000]}")
        return self.askAIAsync("\n".join(prompt_parts), on_success=on_success, on_error=on_error)

    def askAIStream(self, prompt: str, context: str = "",
                    system_prompt: str = "", history: list[dict] = None):
        if not self._client:
            self.streamChunk.emit("AI client not configured.")
            return
        try:
            messages = self._build_messages(prompt, context, system_prompt, history)
            stream = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=4096,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    self.streamChunk.emit(chunk.choices[0].delta.content)
        except Exception as e:
            self.streamChunk.emit(f"\n\n[Error: {e}]")
