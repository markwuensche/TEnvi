# TEnvi: Tunnel Environment Stimulus Generator

TEnvi is a Python toolkit for building controlled **tunnel-motion visual stimuli** for perception and psychophysics experiments. It includes:

- a GUI for interactive tuning and one-off exports,
- a batch exporter for reproducible stimulus sets,
- and a shared rendering pipeline that keeps output behavior consistent across interfaces.

Exports are written as MP4 videos and accompanied by per-stimulus settings JSON files.

## Features

- **Interactive GUI** (`Stimulus Creation/GUI.py`)
  - Live parameter control (geometry, speed, color/brightness, markers, fading)
  - Renderer selection (software / ModernGL, when available)
  - Direct MP4 export

- **Batch generation** (`Stimulus Creation/batch_exporter.py`)
  - Parameter-grid generation for systematic studies
  - Predefined experiment presets (`pilot`, `pilotdepth`, `pilotinfinity`, etc.)
  - CSV manifest output (`stimuli.csv`) describing generated conditions

- **Interactive command-line protocol** (`Stimulus Creation/interactive_protocol.py`)
  - Guided prompts for selecting presets or custom parameters
  - Uses the same export backend as GUI and batch mode

- **Shared rendering/export pipeline** (`Stimulus Creation/tunnel_module.py`)
  - Central parameter defaults and filename generation
  - Frame rendering and FFmpeg-based MP4 encoding
  - Sidecar parameter snapshots for reproducibility

## Repository structure

```text
TEnvi/
├── Stimulus Creation/
│   ├── GUI.py
│   ├── batch_exporter.py
│   ├── interactive_protocol.py
│   ├── tunnel_module.py
│   └── SMOOTHING_NOTES.md
├── CITATION.cff
├── LICENSE
└── README.md
```

## Requirements

- Python 3.9+
- Dependencies:
  - `numpy`
  - `opencv-python`
  - `PyQt5`
  - `moderngl` *(optional; only needed for GPU backend)*
- **FFmpeg** available on your `PATH`

## Installation

1. Clone the repository:

   ```bash
   git clone <your-repo-url>
   cd TEnvi
   ```

2. Install Python dependencies:

   ```bash
   pip install numpy opencv-python PyQt5 moderngl
   ```

   If you only use the software renderer, `moderngl` is optional.

3. Install FFmpeg and verify:

   ```bash
   ffmpeg -version
   ```

## Quick start

### Launch the GUI

```bash
python "Stimulus Creation/GUI.py"
```

Use the controls to adjust tunnel parameters and click export to render an MP4.

### Run a predefined batch

```bash
python "Stimulus Creation/batch_exporter.py" pilot
```

You will be prompted for an output folder name. The run writes videos plus `stimuli.csv`.

### Use the guided CLI protocol

```bash
python "Stimulus Creation/interactive_protocol.py"
```

Follow prompts to run a preset or custom JSON parameter set.

## Reproducibility notes

- All interfaces route through the same export logic, reducing mode-to-mode drift.
- Each exported video includes a matching settings JSON snapshot.
- Batch runs generate a CSV manifest to support downstream analysis and audit trails.

## Citation

If you use TEnvi in research outputs, please cite using `CITATION.cff`.

## License

This project is distributed under the **MIT License**. See `LICENSE` for details.
