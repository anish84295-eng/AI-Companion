from PySide6.QtCore import QObject, Signal
from PIL import Image
from ai_companion.core.ai_engine import AIEngine
from ai_companion.core.screen_capture import ScreenCapture
from openai import OpenAI
from ai_companion.core.config import get_api_key, get_model, get_base_url
import base64
from io import BytesIO
from typing import Optional


VISION_MODEL = "google/gemini-2.0-flash-001"


class VisionAnalyzer(QObject):
    analysisReady = Signal(str)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ai = AIEngine(self)
        self._capture = ScreenCapture()

    def analyzeScreen(self) -> str:
        try:
            img = self._capture.captureScreen()
            if img is None:
                return "Failed to capture screen"
            return self.analyzeImage(img)
        except Exception as e:
            return f"Screen analysis error: {e}"

    def analyzeImage(self, image: Image.Image) -> str:
        try:
            api_key = get_api_key()
            if not api_key:
                return "AI client not configured. Set OPENROUTER_API_KEY in .env"
            base_url = get_base_url()
            client = OpenAI(api_key=api_key, base_url=base_url)
            buf = BytesIO()
            image.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            response = client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Analyze this screenshot. Identify any visible errors, "
                            "code, terminal output, or issues. Provide a brief analysis."
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this screenshot for errors or issues:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2048,
            )
            text = response.choices[0].message.content
            self.analysisReady.emit(text)
            return text
        except Exception as e:
            err = f"Vision analysis failed: {e}"
            self.error.emit(err)
            return err
