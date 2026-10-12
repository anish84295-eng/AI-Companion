from PySide6.QtCore import QObject, Signal, QThread
from ai_companion.core.ai_engine import AIEngine
from ai_companion.core.context_engine import ContextEngine
from ai_companion.core.database import (
    save_message, create_conversation, get_conversations,
    get_messages_for_conversation, save_error
)
from typing import Optional


class ChatManager(QObject):
    messageSent = Signal(str, str)
    responseReceived = Signal(str)
    streamChunk = Signal(str)
    streamDone = Signal(str)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ai = AIEngine(self)
        self._context = ContextEngine()
        self._conversation_id: Optional[int] = None
        self._history: list[dict] = []
        self._streaming = False

    def sendMessage(self, content: str) -> str:
        if not self._conversation_id:
            self._conversation_id = create_conversation()
        save_message(self._conversation_id, "user", content)
        self._history.append({"role": "user", "content": content})
        self.messageSent.emit("user", content)
        context = self._context.getFullContext()
        system_prompt = (
            "You are AI-Companion, a helpful coding assistant embedded in a desktop app. "
            "When explaining errors, provide:\n"
            "1. **Explanation**: What the error means\n"
            "2. **Cause**: Why it happened\n"
            "3. **Fix**: How to fix it\n"
            "4. **Corrected Code**: The fixed code if applicable\n\n"
            "Be concise, clear, and helpful. Use markdown for code blocks."
        )
        try:
            response = self._ai.askAI(content, context=context,
                                       system_prompt=system_prompt,
                                       history=self._history[:-1])
            save_message(self._conversation_id, "assistant", response)
            self._history.append({"role": "assistant", "content": response})
            self.responseReceived.emit(response)
            return response
        except Exception as e:
            err = f"Failed to get AI response: {e}"
            self.error.emit(err)
            return err

    def sendMessageAsync(self, content: str):
        if not self._conversation_id:
            self._conversation_id = create_conversation()
        save_message(self._conversation_id, "user", content)
        self._history.append({"role": "user", "content": content})
        self.messageSent.emit("user", content)
        conv_id = self._conversation_id
        context = self._context.getFullContext()
        system_prompt = (
            "You are AI-Companion, a helpful coding assistant embedded in a desktop app. "
            "When explaining errors, provide:\n"
            "1. **Explanation**: What the error means\n"
            "2. **Cause**: Why it happened\n"
            "3. **Fix**: How to fix it\n"
            "4. **Corrected Code**: The fixed code if applicable\n\n"
            "Be concise, clear, and helpful. Use markdown for code blocks."
        )
        history_snapshot = list(self._history[:-1])

        def on_success(response):
            save_message(conv_id, "assistant", response)
            self._history.append({"role": "assistant", "content": response})
            self.responseReceived.emit(response)

        def on_error(err):
            self.error.emit(err)

        self._ai.askAIAsync(content, context=context, system_prompt=system_prompt,
                            history=history_snapshot, on_success=on_success,
                            on_error=on_error)

    def displayResponse(self, response: str):
        self.responseReceived.emit(response)

    def clearChat(self):
        self._history.clear()
        self._conversation_id = None

    def setCurrentConversation(self, conversation_id: int):
        self._conversation_id = conversation_id
        messages = get_messages_for_conversation(conversation_id)
        self._history = [{"role": m["role"], "content": m["content"]} for m in messages]

    def getConversations(self) -> list[dict]:
        return get_conversations()

    def newConversation(self, title: str = "New Chat") -> int:
        self._conversation_id = create_conversation(title)
        self._history.clear()
        return self._conversation_id

    def explainError(self, error_info: dict, ocr_text: str = ""):
        if not self._conversation_id:
            self._conversation_id = create_conversation(title="Error Explanation")
        context = self._context.buildErrorMessage(error_info)
        if ocr_text:
            context = f"{context}\n\nScreen OCR:\n{ocr_text[:2000]}"
        save_message(self._conversation_id, "user", f"Explain this error:\n{context}")
        self._history.append({"role": "user", "content": f"Explain this error:\n{context}"})
        self.messageSent.emit("user", f"Explain this error:\n{context}")
        try:
            response = self._ai.analyzeError(error_info, ocr_text=ocr_text)
            save_message(self._conversation_id, "assistant", response)
            self._history.append({"role": "assistant", "content": response})
            self.responseReceived.emit(response)
            save_error(
                language=error_info.get("language", "unknown"),
                error_type=error_info.get("error_type", ""),
                error_message=error_info.get("error_message", ""),
                file_name=error_info.get("file_name", ""),
                line_number=error_info.get("line_number", 0),
                severity=error_info.get("severity", "info"),
            )
            return response
        except Exception as e:
            err = f"Failed to explain error: {e}"
            self.error.emit(err)
            return err

    def explainErrorAsync(self, error_info: dict, ocr_text: str = ""):
        if not self._conversation_id:
            self._conversation_id = create_conversation(title="Error Explanation")
        context = self._context.buildErrorMessage(error_info)
        if ocr_text:
            context = f"{context}\n\nScreen OCR:\n{ocr_text[:2000]}"
        save_message(self._conversation_id, "user", f"Explain this error:\n{context}")
        self._history.append({"role": "user", "content": f"Explain this error:\n{context}"})
        self.messageSent.emit("user", f"Explain this error:\n{context}")
        conv_id = self._conversation_id
        snapshot = dict(error_info)
        context_text = ocr_text

        def on_success(response):
            save_message(conv_id, "assistant", response)
            self._history.append({"role": "assistant", "content": response})
            self.responseReceived.emit(response)
            save_error(
                language=snapshot.get("language", "unknown"),
                error_type=snapshot.get("error_type", ""),
                error_message=snapshot.get("error_message", ""),
                file_name=snapshot.get("file_name", ""),
                line_number=snapshot.get("line_number", 0),
                severity=snapshot.get("severity", "info"),
            )

        def on_error(err):
            self.error.emit(err)

        self._ai.analyzeErrorAsync(snapshot, ocr_text=context_text,
                                   on_success=on_success, on_error=on_error)

    def isConnected(self) -> bool:
        return self._ai.isConnected()

    def shutdown(self, timeout_ms: int = 8000):
        import time
        threads = list(self._ai._request_threads)
        deadline = time.time() + timeout_ms / 1000.0
        for t in threads:
            remaining = int((deadline - time.time()) * 1000)
            if remaining <= 0 or not t.isRunning():
                continue
            t.wait(remaining)
            self._ai._request_threads.discard(t)
        return not any(t.isRunning() for t in threads)
