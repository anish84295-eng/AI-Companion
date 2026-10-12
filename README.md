# AI-Companion

A floating animated AI companion for your desktop that monitors your screen, detects programming errors, and provides real-time explanations and fixes.

## Features

- **Floating Cat Companion**: Animated cat sits on top of your screen, draggable, with idle/analyzing/thinking/alert states
- **Screen Monitoring**: Periodically captures screen, skips unchanged frames via perceptual hash, runs OCR
- **Error Detection**: Parses Python tracebacks, JS/TS errors, Java exceptions, C/C++ compiler errors
- **AI-Powered Explanations**: Sends errors to OpenRouter (or OpenAI), returns Explanation, Cause, Fix, and Corrected Code
- **Chat Interface**: Full chat UI with markdown rendering, code blocks, typing indicators
- **Watchdog + pyflakes**: Monitors .py files for changes and runs static analysis
- **System Tray**: Minimize to tray, quick toggle monitoring
- **Dark/Light Theme**: Polished dark theme by default
- **SQLite Storage**: All messages, errors, memory, and settings persisted

## Requirements

- Python 3.11+
- Tesseract OCR installed and in PATH
- OpenRouter API key (free tier available, no credit card needed)

## Setup

### 1. Get a free OpenRouter API key

1. Go to [openrouter.ai](https://openrouter.ai) and sign up (Google/GitHub login works)
2. Go to **Keys** in the sidebar and create a new key
3. Copy the key (starts with `sk-or-v1-...`)
4. You can add a small credit ($5 lasts a long time) or use free models

### 2. Configure the app

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and paste your key:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3-haiku
```

The defaults work well:
- **Chat model**: `anthropic/claude-3-haiku` (fast, cheap, smart)
- **Vision model**: `google/gemini-2.0-flash-001` (excellent at reading screenshots)

## Running

```bash
python run.py
```

## Building Executable

```bash
pip install pyinstaller
pyinstaller build_exe.spec
```

The executable will be in `dist/AI-Companion/`.

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Project Structure

```
ai_companion/
  core/
    database.py        # SQLite DB layer
    config.py          # Environment config (OpenRouter)
    screen_capture.py  # Screen capture with mss
    screen_monitor.py  # Monitor thread
    ocr_engine.py      # Tesseract OCR
    error_detector.py  # Multi-language error parsing
    file_watcher.py    # Watchdog + pyflakes
    context_engine.py  # Context building
    ai_engine.py       # OpenRouter API integration
    vision_analyzer.py # Vision via OpenRouter
    chat_manager.py    # Chat orchestration
  ui/
    theme.py           # Colors, palette, QSS
    widgets.py         # Reusable UI components
    main_window.py     # Main application window
    companion.py       # Floating cat widget
    toasts.py          # Toast notifications
    tray.py            # System tray
run.py                 # Entry point
```

## Architecture

- All screen capture, OCR, and AI calls run on background QThreads
- UI never freezes
- Every external call is wrapped in try/except
- API key loaded from `.env` only (OpenRouter primary, OpenAI fallback)
- Fingerprint-based error deduplication
- Perceptual hash frame skipping
