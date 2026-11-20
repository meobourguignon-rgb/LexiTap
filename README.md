# Translater — Instant Text Translation for Windows

**Translater** is a lightweight, portable Windows utility that lets you translate selected text directly from any application using global keyboard shortcuts.

Select text, press a hotkey, and get your translation instantly. No need to switch windows, open a browser, or manually copy text into a translator.

The application runs in the background, supports the Windows system tray, and requires no installation. Simply launch `start.bat` or run the standalone `Translater.exe`.

## Features

### Global Hotkeys

| Shortcut | Action |
| --- | --- |
| `Ctrl + Alt + Home` | Copies the selected text, translates it into Russian, and displays the result in a floating notification |
| `Ctrl + Alt + End` | Selects all content in the active input field, translates it into English, replaces the original text, and presses `Enter` |
| `Ctrl + Alt + Q` | Exits the application |

### Additional Features

- **Works across applications.** Compatible with browsers, messengers, email clients, text editors, and other applications that support standard text copying.
- **Automatic sending.** English translations can be automatically inserted into the active input field and submitted by pressing `Enter`. This feature can be disabled in Settings.
- **Non-intrusive translation window.** The translation popup does not steal focus or appear in the `Alt + Tab` window switcher.
- **Long text support.** Translation results can be scrolled using the mouse wheel. Translations longer than 40 words remain visible until manually dismissed.
- **System tray integration.** Closing the main window minimizes the application to the system tray without terminating it.
- **Customizable settings.** Configure hotkeys, notification sounds, automatic sending, and startup hints directly from the application.

## Getting Started

There are two ways to run Translater: using Python or launching the standalone executable.

### Option 1: Run with Python

1. Launch `start.bat`.
2. The script automatically creates a `.venv` virtual environment and installs the required dependencies from `requirements.txt`.
3. Once the application starts, you can use its global hotkeys in any supported application.

Closing the main window does not terminate the application. It continues running in the system tray.

### Option 2: Standalone Executable

Download the latest `Translater.exe` from the [Releases](../../releases/latest) page.

No Python installation or additional dependencies are required. The application is packaged into a single standalone executable.

On the first launch, the following files and directories are automatically created next to the executable:

- `config.json` — application configuration.
- `logs/` — application log files.

## Building the Executable

To build Translater yourself, you need Python 3.10 or newer.

Run the following commands from the project root directory:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe build.py
```

The `build.py` script uses PyInstaller to create a standalone `Translater.exe` and places it in the project root directory.

The resulting executable can be copied to another Windows computer and run without installing Python.

Application icons are stored in the `assets/` directory. If you replace `image.jpg`, regenerate the icons using:

```bat
.venv\Scripts\python.exe tools\make_icon.py
```

### Automated Releases

GitHub Actions can automatically build and publish new releases.

Pushing a Git tag matching `v*` triggers the release workflow, which builds the executable and attaches `Translater.exe` to a GitHub Release.

Example:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## How It Works

1. **Global hotkeys:** Windows `RegisterHotKey` captures keyboard shortcuts in a dedicated thread. Events are passed to the Tkinter main thread through `queue.Queue` and `after()`.
2. **Text extraction:** The application uses `Ctrl+C` to copy selected text. For English translation, it also uses `Ctrl+A` to select the entire contents of the active input field. The previous clipboard contents are restored afterward.
3. **Translation:** Text is translated using the unofficial Google Translate `translate_a/single` endpoint. If the primary provider fails, MyMemory is used as a fallback. No API keys are required, and translation results are cached during the current session.
4. **Displaying results:** Translations are either displayed in a floating notification or inserted directly into the active input field, depending on the selected hotkey.

## Configuration

The `config.json` file is stored next to the application executable or in the project root when running from source.

Settings changed through the application's Settings window are saved automatically. If you edit the configuration file manually, restart the application for the changes to take effect.

Default configuration:

```json
{
  "hotkeys": {
    "to_russian": "ctrl+alt+home",
    "to_english": "ctrl+alt+end",
    "quit": "ctrl+alt+q"
  },
  "toast": {
    "size": 400,
    "margin": 24,
    "duration_seconds": 8,
    "max_source_chars": 220
  },
  "translation": {
    "timeout_seconds": 8,
    "max_chars": 2000,
    "providers": ["google", "mymemory"],
    "auto_send": true
  },
  "sound": {
    "enabled": true,
    "notify_file": "notify.wav",
    "error_file": "error.wav"
  },
  "show_startup_hint": true
}
```

### Configuration Options

- `hotkeys` — keyboard shortcuts. Supported modifiers: `ctrl`, `alt`, `shift`, and `win`. Supported keys include letters (`a`–`z`), numbers (`0`–`9`), `home`, `end`, `f1`–`f12`, and others.
- `toast.size` — notification window size in pixels (240–800).
- `translation.timeout_seconds` — maximum time allowed for a translation request.
- `translation.max_chars` — maximum text length accepted for translation.
- `translation.providers` — translation providers in priority order.
- `translation.auto_send` — automatically presses `Enter` after inserting an English translation.
- `sound.enabled` — enables or disables notification sounds.
- `show_startup_hint` — controls whether the startup hint is displayed.

## Project Structure

```text
portable-translator/
├── translator.py          # Entry point: theme setup and app startup
├── ctkmaker.py            # Base CTkScript class for behavior scripts
├── scripts/               # Home, Settings, and Exit button behavior
├── translator_core/
│   ├── app.py             # Controller: events, hotkeys, tray, translations
│   ├── ui.py              # CTkMaker screens (MainWindow, Settings)
│   ├── clipboard.py       # Clipboard operations via Win32 SendInput
│   ├── config.py          # Configuration loading and validation
│   ├── hotkeys.py         # Global hotkeys using RegisterHotKey
│   ├── icon.py            # Window, tray, and notification icons
│   ├── language.py        # Language detection and text preparation
│   ├── notification.py   # Floating translation notification
│   ├── paths.py           # Paths for source and one-file builds
│   ├── providers.py       # Google / MyMemory translation and caching
│   ├── sound.py           # WAV generation and playback
│   └── tray.py            # System tray icon and menu
├── assets/                 # Images, icons, and sounds
├── tools/
│   └── make_icon.py       # Generates app.jpg / app.ico from image.jpg
├── image.jpg               # Source image for application icons
├── config.json             # Default configuration
├── build.py                # Builds standalone Translater.exe
├── requirements.txt        # Runtime and build dependencies
├── LICENSE                 # MIT License
├── .github/workflows/      # Automated release builds
└── start.bat               # Launches the app and creates .venv if needed
```

The following files and directories are generated locally and are excluded from version control through `.gitignore`:

- `logs/`
- `.venv/`
- `build/`
- `dist/`
- `Translater.exe`

## Dependencies

- [`ctkmaker-core`](https://github.com/kandelucky/ctkmaker-core) — a fork of CustomTkinter that supports additional generated-code arguments such as `full_circle`, `font_wrap`, `pressed_color`, and `register_project_fonts`. The standard `customtkinter` package is not compatible and must not be installed alongside this fork.
- `Pillow` — image processing and icon generation.
- `pystray` — system tray integration.
- `PyInstaller` — used only when building the standalone executable.

The `Cascadia Code SemiBold` font is included with Windows 10 and Windows 11, so no separate font installation is required.

## Limitations

- Translation works only in applications that support standard text copying with `Ctrl+C`. Some PDF readers, terminals, and games may not expose their text content through the clipboard.
- Only text clipboard contents are restored. If the clipboard contains an image or a file, that content may be lost.
- If the target application is running with administrator privileges, Translater must also be launched as administrator. Otherwise, Windows may block keyboard input simulation.
- Translation requires an internet connection. Text is sent to Google Translate or MyMemory. The fallback provider may help when the primary service is unavailable, but offline translation is not supported.

## Logs

Application logs are stored in:

```text
logs\translator.log
```

## License

This project is licensed under the [MIT License](LICENSE).
