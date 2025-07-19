# Voice Viewer

Professional audio visualizer for faceless content creators and developers.

## Install

### macOS Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or venv/bin/activate.fish for fish shell

# IMPORTANT: Install PortAudio first (required for PyAudio)
brew install portaudio

# Install all dependencies (including PyAudio for live mode)
pip install -r requirements.txt
```

### Linux Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio

# Or for CentOS/RHEL/Fedora:
# sudo yum install portaudio-devel
# sudo dnf install portaudio-devel

# Install Python dependencies
pip install -r requirements.txt
```

### Windows Installation

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies (PyAudio should work without additional setup)
pip install -r requirements.txt
```

### If PyAudio Installation Fails

If you encounter issues installing PyAudio, you can still use the core features:

```bash
# Install without PyAudio
pip install librosa numpy opencv-python moviepy soundfile matplotlib click rich pydantic scipy pillow tqdm imageio-ffmpeg

# Live microphone mode will be disabled, but file-based generation works
```

## Quick Start

```bash
# Generate visualization from audio file
python -m voice_viewer generate input.wav --output devlog.mp4

# Live microphone mode (requires PyAudio)
python -m voice_viewer live --theme minimal --save-config my_settings.json

# Use saved config for high-quality render
python -m voice_viewer generate input.wav --config my_settings.json --resolution 1080p

# Config file overrides other parameters
python -m voice_viewer generate input.wav --config tuned_params.json --output final.mp4

# Preview from file
python -m voice_viewer preview input.wav

# Professional theme for technical content
python -m voice_viewer generate input.wav \
  --visualizer spectrum \
  --theme professional \
  --output devlog.mp4

# Minimal white-on-black circular design
python -m voice_viewer generate input.wav \
  --theme minimal \
  --output clean.mp4
```

## Features

- **Live microphone mode** - Real-time parameter tuning with TUI controls
- **Configuration export** - Save settings from live mode for production renders
- **Multiple visualizers** - Waveform, spectrum, circular with nested circles
- **Professional themes** - Clean aesthetics for technical content
- **Minimal theme** - Simple white-on-black circular design
- **Perfect sync** - Frame-accurate audio/video synchronization
- **High quality** - Up to 4K export with professional codecs
- **Real-time preview** - See results before rendering
- **Adaptive amplification** - Automatically boosts quiet frequencies for better visuals

Perfect for devlogs, tutorials, and anonymous content creation.

## Workflow

1. **Tune Live**: Use `live` mode with microphone to find perfect settings
2. **Save Config**: Export your tuned parameters to a JSON file
3. **Render High-Quality**: Use saved config with `generate` for final video

This workflow lets you quickly iterate and find the perfect visual settings before committing to a long render.

## Troubleshooting

### PyAudio Installation Issues

**macOS**: "portaudio.h file not found"
```bash
# Install PortAudio via Homebrew first
brew install portaudio
pip install pyaudio
```

**macOS Alternative**: Use conda instead of pip
```bash
conda install pyaudio
```

**Linux**: Missing PortAudio development headers
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev

# CentOS/RHEL/Fedora  
sudo dnf install portaudio-devel
```

**All Platforms**: Skip PyAudio if installation fails
```bash
# Core functionality works without PyAudio
# Only live microphone mode requires it
python -m voice_viewer generate audio.mp3  # This works
python -m voice_viewer live                # This requires PyAudio
```

### Common Issues

**"No module named 'pyaudio'"** when using live mode:
- Install PyAudio following platform-specific instructions above
- Or use file-based workflow instead

**Audio not detecting microphone**:
- Check microphone permissions in System Preferences (macOS)
- Test microphone in other applications first
- Try different microphone if available

## License

CC0 1.0 Universal (Public Domain)