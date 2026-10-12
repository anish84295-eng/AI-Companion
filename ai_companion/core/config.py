from pathlib import Path
from dotenv import load_dotenv, set_key
import os

from ai_companion.core.paths import data_path

_ENV_PATH = data_path(".env")
load_dotenv(_ENV_PATH, override=True)


def _ensure_env():
    if not _ENV_PATH.exists():
        _ENV_PATH.touch()


def get_api_key() -> str:
    provider = os.getenv("AI_PROVIDER", "openrouter")
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", "")
    elif provider == "custom":
        return os.getenv("CUSTOM_API_KEY", "")
    return os.getenv("OPENROUTER_API_KEY", "")


def get_model() -> str:
    provider = os.getenv("AI_PROVIDER", "openrouter")
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4o")
    elif provider == "custom":
        return os.getenv("CUSTOM_MODEL", "")
    return os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-haiku")


def get_base_url() -> str:
    provider = os.getenv("AI_PROVIDER", "openrouter")
    if provider == "openai":
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    elif provider == "custom":
        return os.getenv("CUSTOM_BASE_URL", "")
    return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


def get_provider() -> str:
    return os.getenv("AI_PROVIDER", "openrouter")


def set_provider(provider: str):
    _ensure_env()
    set_key(str(_ENV_PATH), "AI_PROVIDER", provider)
    os.environ["AI_PROVIDER"] = provider


def set_api_key(key: str):
    _ensure_env()
    provider = get_provider()
    if provider == "openai":
        var = "OPENAI_API_KEY"
    elif provider == "custom":
        var = "CUSTOM_API_KEY"
    else:
        var = "OPENROUTER_API_KEY"
    set_key(str(_ENV_PATH), var, key)
    os.environ[var] = key


def set_model(model: str):
    _ensure_env()
    provider = get_provider()
    if provider == "openai":
        var = "OPENAI_MODEL"
    elif provider == "custom":
        var = "CUSTOM_MODEL"
    else:
        var = "OPENROUTER_MODEL"
    set_key(str(_ENV_PATH), var, model)
    os.environ[var] = model


def set_base_url(url: str):
    _ensure_env()
    provider = get_provider()
    if provider == "openai":
        var = "OPENAI_BASE_URL"
    elif provider == "custom":
        var = "CUSTOM_BASE_URL"
    else:
        var = "OPENROUTER_BASE_URL"
    set_key(str(_ENV_PATH), var, url)
    os.environ[var] = url


def get_tesseract_path() -> str:
    path = os.getenv("TESSERACT_PATH", "")
    if not path:
        import shutil
        found = shutil.which("tesseract")
        if found:
            return found
    return path


def test_connection() -> tuple[bool, str]:
    try:
        from openai import OpenAI
        api_key = get_api_key()
        if not api_key:
            return False, "Not configured"
        base_url = get_base_url()
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=15.0, max_retries=0)
        client.models.list()
        return True, "Connected"
    except Exception as e:
        return False, f"Failed: {str(e)[:60]}"
