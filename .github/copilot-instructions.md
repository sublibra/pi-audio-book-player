# Raspberry Pi Audiobook Player - Copilot Instructions

## Repository Overview

**Type**: Raspberry Pi GPIO-controlled hardware project  
**Purpose**: GPIO button and LED-controlled audiobook player using madplay for audio playback  
**Size**: Small (~350 lines of Python code across 4 modules)  
**Language**: Python 3.13+  
**Target Platform**: Raspberry Pi (with mock mode for testing on any Linux system)  
**External Dependencies**: madplay (audio player), gpiozero (GPIO control; prefers lgpio or RPi.GPIO backend on Pi)

## Project Architecture

This is a single-threaded Python application with three main components:

### Core Files (in root directory)
- **main.py** - Entry point, orchestrates all components, handles button callbacks and state management
- **audio_player.py** - Manages madplay subprocess, playback control, seek operations, and sleep timer
- **gpio_controller.py** - Abstraction layer for GPIO (supports both real Raspberry Pi GPIO and mock keyboard mode)
- **state_manager.py** - JSON-based persistence for book index and playback position

### Configuration Files
- **config.json** - Main configuration (audiobook paths, GPIO pin assignments, timers). CRITICAL: This file is gitignored and user-specific. A template exists at `.config.json`.
- **audiobook_state.json** - Runtime state file (current book, position). Gitignored, auto-generated.
- **pyproject.toml** - Python project metadata (minimal, uses uv)
- **requirements.txt** - Python dependencies (GPIO libraries, platform-conditional)

### Key Features
- 6 button inputs (play/pause, sleep timer, next/prev book, forward/backward seek)
- 7 LED outputs (one per audiobook to show active book)
- Auto-save state every 5 seconds
- Sleep timer that pauses playback after configured minutes
- Mock mode for testing without Raspberry Pi hardware

## Build & Run Instructions

### System Dependencies
**ALWAYS install madplay before running the application:**
```bash
# On Raspberry Pi or Debian/Ubuntu:
sudo apt-get update
sudo apt-get install madplay
```

### Python Dependencies

**IMPORTANT**: GPIO stack is handled by gpiozero:
- `gpiozero` is required everywhere (works in mock mode without hardware)
- On Raspberry Pi (armv7l/aarch64) gpiozero will prefer `lgpio` or `RPi.GPIO` backends (both are conditional in requirements.txt)
- On x86_64 Linux systems (mock mode), backend libs aren't needed; ignore install errors for them

**Install Python dependencies using ONE of these methods:**

#### Method 1: Using pip (standard)
```bash
pip3 install -r requirements.txt
```
**Note**: On non-ARM systems, ignore GPIO installation errors - they're not needed for mock mode.

### Configuration Setup

**CRITICAL**: Before first run, you MUST create config.json:
```bash
cp .config.json config.json
# Edit config.json and add your audiobook paths
```

The application will fail immediately if config.json doesn't exist or audiobook paths are invalid.

### Running the Application

**On Raspberry Pi (with GPIO hardware):**
```bash
python3 main.py
```

**On any Linux system (mock mode for testing):**
```bash
python3 main.py --mock
```

**Mock mode keyboard controls:**
- `p` - Play/Pause
- `s` - Sleep Timer  
- `n` - Next Book
- `b` - Previous Book (back)
- `f` - Forward 1 min
- `r` - Rewind 1 min
- `q` - Quit

**Custom config file:**
```bash
python3 main.py --config /path/to/config.json
```

### Validation Steps

1. **Check madplay is installed**: `which madplay` (must return `/usr/bin/madplay`)
2. **Test help**: `python3 main.py --help` (should show usage without errors)
3. **Test mock mode**: `timeout 3 python3 main.py --mock` (should start, show GPIO setup, then timeout)
4. **Verify config exists**: File `config.json` must exist with valid audiobook paths

## Testing & CI/CD

**IMPORTANT**: This repository has NO automated tests, NO CI/CD pipelines, NO GitHub Actions workflows, NO linting configuration, and NO test files.

Any changes should be manually validated by:
1. Running `python3 main.py --help` to verify no syntax errors
2. Running `python3 main.py --mock` to test in mock mode
3. On Raspberry Pi, testing with actual hardware buttons and LEDs

## Code Architecture Details

### Threading Model
- Main thread: Handles button callbacks and event loop
- Auto-save thread: Daemon thread saving state every 5 seconds
- Playback monitor thread: Tracks madplay process and updates position
- Mock GPIO keyboard thread: Reads keyboard input in mock mode

### State Management
- Position is calculated from elapsed time (not queried from madplay)
- State is saved on every button press AND every 5 seconds during playback
- Pausing accumulates pause duration to maintain accurate position

### GPIO Abstraction
- `GPIOInterface` abstract class enables testing without hardware
- `RaspberryPiGPIO` uses gpiozero `Button`/`LED` (pull-up buttons, bounce_time=0.3)
- `MockGPIO` uses termios for keyboard input on Linux systems

### Audio Playback
- madplay runs as subprocess (not a Python library)
- Process control uses SIGSTOP/SIGCONT for pause/resume
- Seeking requires stopping and restarting with new `--start` position
- Process cleanup uses process groups (preexec_fn=os.setsid) for clean termination

## Important Implementation Details

### Known Issues & Workarounds

1. **gpiozero backend choice**: On Raspberry Pi, gpiozero will pick an available backend (`lgpio` or `RPi.GPIO`). Ensure at least one backend library installs; otherwise hardware mode will fail to start.

2. **Hardcoded Sleep**: main.py line 191 uses `time.sleep(1)` in the main loop - this is intentional for low CPU usage.

3. **No Position Query from madplay**: Position is calculated by tracking elapsed time, not queried from madplay, as madplay doesn't provide a query interface.

4. **Announcement Blocking**: The `play_announcement()` method blocks until announcement completes (uses subprocess.run with wait). Book switching will pause until announcement finishes.


### File Paths

- All configuration is at repository root (no subdirectories)
- No `src/`, `tests/`, or other package structure
- Python files are direct modules, not a package
- State files (config.json, audiobook_state.json) are created in working directory

### Python Version

- Project specifies `requires-python = ">=3.13"` in pyproject.toml
- Tested working on Python 3.13.7
- Uses modern Python features (f-strings, type hints, subprocess features)

## Repository Files Reference

### Root Directory Contents
```
.config.json          # Config template (gitignored: config.json)
.git/                 # Git repository
.gitignore           # Excludes config.json, audiobook_state.json, __pycache__, venv
README.md            # User documentation with hardware setup and usage
__pycache__/         # Python bytecode cache
audio_player.py      # AudioPlayer class (~300 lines)
audiobook_state.json # Runtime state (auto-generated, gitignored)
config.json          # User configuration (gitignored, must be created)
gpio_controller.py   # GPIOController, GPIOInterface, implementations (~230 lines)
main.py              # Entry point, AudiobookPlayer class (~220 lines)
pyproject.toml       # Python project metadata (minimal)
requirements.txt     # Python dependencies (4 lines, conditional imports)
state_manager.py     # StateManager class (~75 lines)
```

### .gitignore Contents
- config.json and audiobook_state.json (user-specific files)
- Standard Python patterns (__pycache__, *.pyc, venv, .pytest_cache, etc.)
- No build artifacts (no build directory, no dist/)

## Change Validation Checklist

When making code changes, ALWAYS:

1. **Verify syntax**: Run `python3 main.py --help` (should not error)
2. **Test mock mode**: Run `python3 main.py --mock` and test keyboard controls
3. **Check imports**: If adding new stdlib imports, verify Python 3.13+ compatibility
4. **Preserve threading**: Don't add blocking calls in the main thread or button callbacks
5. **Test config loading**: Ensure config.json parsing still works after changes
6. **Signal handling**: Don't break SIGINT/SIGTERM handlers (Ctrl+C must clean up properly)

## Common Pitfalls to Avoid

1. **Don't assume GPIO libraries are installed** on development machines - always use mock mode for testing
2. **Don't call blocking operations in button callbacks** - they run in GPIO event threads
3. **Don't modify state without locking** - use `state_manager.position_lock` when needed
4. **Don't create config.json in repository** - it's gitignored for security (contains file paths)
5. **Don't use libraries not in requirements.txt** - keep dependencies minimal for Raspberry Pi
6. **Don't assume madplay is installed** - check and document installation requirement

## Trust These Instructions

These instructions are based on comprehensive repository analysis including:
- Full code review of all Python modules
- Testing application in mock mode
- Verification of dependencies and build process
- Analysis of configuration files and state management

**Only perform additional searches or exploration if:**
- These instructions are incomplete for your specific task
- You find information here that contradicts actual code behavior
- You're implementing a new feature requiring deep architectural understanding

Otherwise, trust this documentation to minimize exploration time and focus on implementing changes efficiently.
