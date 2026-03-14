# Time and Space Stimulus Toolkit

A set of Python tools for generating tunnel-style visual stimuli for perceptual experiments. The toolkit provides a Qt GUI for interactive previews, batch and interactive command-line exporters, and a shared rendering pipeline that produces consistent MP4 outputs with embedded silent audio.

## Repository layout
- **Stimulus Creation/** contains the actively maintained stimulus generator:
  - `GUI.py` launches the Qt control panel used for previews and single exports.
  - `tunnel_module.py` implements the rendering backends, parameter defaults, and the shared export pipeline.
  - `batch_exporter.py` runs parameter grids or custom JSON lists through the exporter and records a CSV manifest.
  - `interactive_protocol.py` offers a guided CLI wrapper around the batch exporter.
- Legacy and analysis assets live alongside these tools for reference (for example, `SMOOTHING_NOTES.md` documents past motion-smoothing fixes).

## Requirements
- Python 3 with NumPy, OpenCV, and PyQt5 installed. ModernGL is optional when using the GPU renderer; the default is the software backend.
- FFmpeg must be available on your `PATH` (or located at `C:\\ffmpeg\\bin\\ffmpeg.exe`) for MP4 creation.

## Running the GUI
1. From the repository root, launch the control panel:
   ```bash
   python "Stimulus Creation/GUI.py"
   ```
2. Adjust parameters such as tunnel dimensions, speed, palettes, and renderer backend. The GUI defaults to the software renderer but also supports ModernGL for GPU-accelerated previews.
3. Use **Export MP4** to render a near-lossless H.264 video. The GUI delegates to the shared export pipeline so GUI, batch, and CLI exports produce identical videos and companion `_settings.json` files.

## Batch exporting
- Run batches by providing variable grids or explicit parameter lists to `batch_exporter.py`. Each export uses the same pipeline as the GUI and writes a row to `stimuli.csv` describing the parameters:
  ```bash
  python "Stimulus Creation/batch_exporter.py" pilot
  ```
- Custom batches can also be supplied via JSON strings when running the script directly, enabling reproducible stimulus sets without the GUI.

## Interactive CLI helper
- `interactive_protocol.py` walks you through presets, manual parameter entry, or JSON input before invoking the batch exporter. It exposes the same parameters as the GUI, including renderer backend selection, motion blur, and temporal oversampling.

## Video rendering pipeline
- All export paths (GUI button, batch exporter, and interactive helper) call `export_video` in `tunnel_module.py`, which renders frames from the software or ModernGL renderer, applies optional temporal oversampling or motion blur, and streams raw BGR frames into FFmpeg.
- FFmpeg encodes the stream as high-profile H.264 with `yuv420p` output, silent stereo audio, and `+faststart` flags for broad compatibility. Each export saves a JSON snapshot of the parameters alongside the MP4.

## Renderer defaults
- The software renderer is the default backend for reliability on machines without stable OpenGL drivers. You can switch to the ModernGL backend from either the GUI dropdown or the interactive prompts when hardware acceleration is available.
