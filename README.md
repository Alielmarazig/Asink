# asynk

Multi-track audio/video synchronization tool. Import clips from multiple cameras and audio recorders, sync them by audio waveform matching, and export aligned timelines for your NLE.

## How it works

asynk extracts audio from every imported clip, downsamples to 8kHz mono, then runs FFT-based cross-correlation against a reference clip. The correlation peak gives the time offset; peak height gives a confidence score. High confidence = reliable sync. Low confidence = the clips may not share overlapping audio.

## Requirements

- Python 3.11+
- FFmpeg (must be on PATH)
- System dependencies for PySide6 (Qt6)

## Setup

```bash
# Clone or download the project
cd asynk

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Usage

1. **Import clips** - drag and drop files onto the window, or use File > Import Clips / Import Folder
2. **Set reference** - pick which clip is the "master" (usually the main camera or dedicated audio recorder)
3. **Sync** - hit the Sync button. Progress shows in the status bar. Each clip gets an offset (seconds) and a confidence score
4. **Export** - choose your NLE format and frame rate, then export

## Supported formats

### Media input
Video: MP4, MOV, AVI, MKV, MXF, WMV, FLV, M4V, MPG, MPEG, TS, WebM, 3GP, R3D, BRAW, ARI
Audio: WAV, MP3, AAC, FLAC, OGG, WMA, M4A, AIFF, OPUS

### Timeline export
- **Final Cut Pro X** (.fcpxml) - v1.9, compatible with FCP X 10.2.3+
- **Adobe Premiere Pro** (.xml) - FCP Interchange v5, works with CS6 through CC 2017+
- **EDL** (.edl) - CMX 3600, compatible with Vegas Pro 13/14, EDIUS 7.5+, and most NLEs

## Project structure

```
asynk/
  asynk/
    core/
      sync_engine.py      # FFT cross-correlation sync
      media_handler.py     # FFmpeg probe + file scanning
    exporters/
      fcpxml.py           # Final Cut Pro X export
      premiere_xml.py     # Premiere Pro XML export
      edl.py              # CMX 3600 EDL export
      export_manager.py   # Unified export interface
    ui/
      main_window.py      # PySide6 desktop interface
  main.py                 # Entry point
  requirements.txt
```

## Confidence thresholds

- **> 50%** (green): strong sync, clips share clear overlapping audio
- **10-50%** (yellow): possible sync, review manually
- **< 10%** (red): likely no shared audio content between clips

## Known limitations

- Sync accuracy depends on audio overlap between clips. Silent or very noisy recordings will produce low-confidence results
- Very long clips (> 5 hours) may use significant memory during correlation
- Camera-native RAW formats (R3D, BRAW, ARI) require their respective codec packages installed alongside FFmpeg
