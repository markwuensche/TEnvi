# Stimulus Smoothness Review

## Observations
- The repository contains multiple legacy stimulus generators alongside the current `TunnelRenderer` used by the GUI and batch exporter. Consolidating on the ModernGL pipeline keeps maintenance manageable, but the unused `_OLD` modules could eventually be archived outside the repo to reduce confusion.
- Preview smoothness in the GUI previously depended on a fixed step of `speed / fps`. Any hiccup in the Qt timer left the virtual camera lagging, which viewers perceived as a momentary slowdown. Motion-blur sampling also assumed a perfectly stable frame cadence.
- Exported videos advanced the camera by incrementing a running position before drawing. This skipped the initial frame at `t=0` and could accumulate floating-point error in extremely long renders.

## Implemented Improvements
- Camera advancement in the preview now uses real elapsed time with an exponential smoothing filter and safety clamp. This keeps the on-screen motion perceptually smooth even when the Qt event loop jitters, while preventing large jumps after pauses.
- Motion-blur sampling in the preview derives its offsets from the actual time delta, so the blur envelope always matches the rendered motion.
- Video exports render the first frame at exactly `t = 0` and derive subsequent camera positions analytically, removing cumulative error and matching the preview timing.
- Parameter validation now enforces a positive `render_scale`, and the duplicated default entry was removed.
- Added a CPU fallback renderer with analytic perspective quads. It avoids GPU read-backs for previews on hardware without stable OpenGL timing, and it shares the same parameter interface as the ModernGL backend.
- Offline renders can oversample time within each frame. Averaging multiple sub-frame camera positions per video frame eliminates strobing at high speeds, yielding perceptually smoother stimuli.

## Further Suggestions
- For offline experiments that demand perfectly smooth motion, consider rendering via Blender's Eevee or Cycles engines using the same tunnel parameters exported from the GUI. Blender provides deterministic frame pacing, support for motion blur, and high-quality anti-aliasing with minimal shimmer.
- If ModernGL remains the preferred renderer, migrating the preview widget to a native `QOpenGLWidget` would allow vsync-synchronised presentation and reduce read-back overhead from the off-screen framebuffer. The CPU fallback ensures production can continue until that migration is prioritised.
- Adding automated tests (even lightweight linting or `python -m compileall`) would help catch regressions in future parameter or GUI refactors.
