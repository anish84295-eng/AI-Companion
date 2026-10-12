from PIL import Image
import pytesseract
from typing import Optional
import re


def _configure_tesseract():
    try:
        from ai_companion.core.config import get_tesseract_path
        path = get_tesseract_path()
        if path:
            pytesseract.pytesseract.tesseract_cmd = path
    except Exception:
        pass


class OCREngine:
    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        else:
            _configure_tesseract()

    def extractText(self, image: Image.Image) -> str:
        try:
            text = pytesseract.image_to_string(image, lang="eng")
            return text.strip()
        except Exception as e:
            print(f"OCR extractText error: {e}")
            return ""

    def extractTextWithConfidence(self, image: Image.Image) -> tuple[str, float]:
        try:
            data = pytesseract.image_to_data(image, lang="eng", output_type=pytesseract.Output.DICT)
            confs = [int(c) for c in data["conf"] if int(c) > 0]
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            text = pytesseract.image_to_string(image, lang="eng")
            return text.strip(), avg_conf / 100.0
        except Exception as e:
            print(f"OCR extractTextWithConfidence error: {e}")
            return "", 0.0

    def processImage(self, image: Image.Image, lang: str = "eng") -> str:
        try:
            text = pytesseract.image_to_string(image, lang=lang)
            return text.strip()
        except Exception as e:
            print(f"OCR processImage error: {e}")
            return ""

    def detectLanguage(self, image: Image.Image) -> str:
        try:
            data = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            return data.get("lang", "eng")
        except Exception:
            return "eng"

    def extractCodeRegions(self, image: Image.Image) -> list[str]:
        try:
            text = self.extractText(image)
            lines = text.split("\n")
            code_lines = []
            in_code = False
            for line in lines:
                stripped = line.strip()
                if any(kw in stripped for kw in ["def ", "class ", "import ", "from ", "function ",
                                                   "const ", "let ", "var ", "if (", "for (",
                                                   "while (", "return ", "print(", "console.",
                                                   "#include", "public ", "private "]):
                    in_code = True
                if in_code:
                    code_lines.append(line)
                    if not stripped and len(code_lines) > 2:
                        in_code = False
            return code_lines if code_lines else lines
        except Exception:
            return []
