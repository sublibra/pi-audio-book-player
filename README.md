# Raspberry Pi Audiobook Player

A GPIO-controlled audiobook player for Raspberry Pi using madplay.

## Features

- **Play/Pause Button**: Start or pause the current audiobook
- **Sleep Timer Button**: Add 15-minute sleep timer when playing
- **Book Navigation**: Switch between 7 different audiobooks
- **Seek Controls**: Jump forward/backward by 1 minute
- **7 LEDs**: Visual indicator showing which book is currently active
- **Auto-Save**: Position saved every 5 seconds
- **Resume Playback**: Automatically resumes from last position on startup

## Hardware Setup

### Buttons (with pull-up resistors)
- GPIO 17: Play/Pause
- GPIO 27: Sleep Timer (+15 min)
- GPIO 22: Next Book
- GPIO 23: Previous Book
- GPIO 24: Forward 1 min
- GPIO 25: Backward 1 min

### LEDs (7 books)
- GPIO 5, 6, 13, 19, 26, 16, 20

## Configuration

Edit `config.json` to:
1. Set paths to your audiobook files
2. Customize GPIO pin assignments
3. Adjust timers and intervals

## Installation

Rename the .config.json to config.json and update it with your audiobook paths.

### On Raspberry Pi

```bash
sudo apt-get update
sudo apt-get install madplay python3-rpi.gpio
pip3 install -r requirements.txt
```

### On Linux (for testing)

```bash
sudo apt-get install madplay
```

## Usage

### On Raspberry Pi
```bash
python3 main.py
```

### On Linux (mock mode)
```bash
python3 main.py --mock
```

In mock mode, you can control playback via keyboard:
- `p`: Play/Pause
- `s`: Sleep Timer
- `n`: Next Book
- `b`: Previous Book (back)
- `f`: Forward 1 min
- `r`: Rewind 1 min
- `q`: Quit

## State Management

The player automatically saves the current book and position to `audiobook_state.json` every 5 seconds. This file is used to resume playback on the next startup.
