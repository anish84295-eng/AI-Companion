import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def resource_path(*parts: str) -> Path:
    if is_frozen():
        base = Path(getattr(sys, "_MEIPASS", app_dir()))
    else:
        base = app_dir()
    return base.joinpath(*parts)


def data_path(*parts: str) -> Path:
    return app_dir().joinpath(*parts)
