import mss
import mss.tools
from PIL import Image
from io import BytesIO
from typing import Optional
import hashlib


class ScreenCapture:
    def __init__(self):
        self._last_hash: Optional[str] = None

    def captureScreen(self) -> Optional[Image.Image]:
        try:
            with mss.MSS() as sct:
                monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                return img
        except Exception as e:
            print(f"ScreenCapture error: {e}")
            return None

    def captureRegion(self, x: int, y: int, w: int, h: int) -> Optional[Image.Image]:
        try:
            region = {"top": y, "left": x, "width": w, "height": h}
            with mss.MSS() as sct:
                sct_img = sct.grab(region)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                return img
        except Exception as e:
            print(f"ScreenCapture region error: {e}")
            return None

    def has_changed(self, img: Image.Image) -> bool:
        try:
            thumb = img.resize((64, 64)).convert("L")
            data = thumb.tobytes()
            h = hashlib.md5(data).hexdigest()
            if h == self._last_hash:
                return False
            self._last_hash = h
            return True
        except Exception:
            return True

    def captureScreenIfChanged(self) -> Optional[Image.Image]:
        img = self.captureScreen()
        if img is None:
            return None
        if self.has_changed(img):
            return img
        return None

    def get_thumbnail(self, img: Image.Image, max_size: int = 400) -> Image.Image:
        try:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            return img
        except Exception:
            return img

    def to_bytes(self, img: Image.Image, fmt: str = "PNG") -> bytes:
        try:
            buf = BytesIO()
            img.save(buf, format=fmt)
            return buf.getvalue()
        except Exception:
            return b""

    def to_pixmap_bytes(self, img: Image.Image) -> bytes:
        return self.to_bytes(img, "PNG")
