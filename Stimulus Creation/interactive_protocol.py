"""Interactive console helper for running ``batch_exporter``.

This script guides users through selecting presets or building custom
parameter grids for video generation without needing to remember
command-line arguments. Run it with ``python interactive_protocol.py`` and
follow the prompts.
"""

import json
import os
import sys
from typing import Any, Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.append(SCRIPT_DIR)

from batch_exporter import generate_param_combinations, prepare_batch_videos
from tunnel_module import apply_palette_color, compute_render_resolution, default_params

PRESETS: Dict[str, Dict[str, Any]] = {
    "pilot": {
        "description": "4 widths × 4 heights for pilot sizing sweep.",
        "variable_spec": {
            "tunnel_width": [1.0, 1.5, 2.0, 2.5],
            "tunnel_height": [1.0, 1.5, 2.0, 2.5],
            "exp_num": ["pilot"],
        },
    },
    "pilotdepth": {
        "description": "Depth and recycling combinations for pilot depth sweep.",
        "variable_spec": {
            "tunnel_depth": [100, 200, 300, 400],
            "recycle_loop": [True, False],
            "exp_num": ["pilot"],
        },
    },
    "pilotinfinity": {
        "description": "Infinity-style depth combinations with two height options.",
        "variable_spec": {
            "tunnel_width": [1.0, 1.5, 2.0, 2.5],
            "tunnel_height": [1.0, 2.0],
            "tunnel_depth": [100, 200, 1000],
            "recycle_loop": [True, False],
            "duration": [5.0],
            "exp_num": ["pilot"],
        },
    },
    "final_pilot": {
        "description": "12 videos: separate 4-level sweeps of width, height, and depth with shaded software rendering.",
        "base_updates": {
            "depth_markers": "shaded",
            "renderer_backend": "software",
            "shaded": True,
            "duration": 5.0,
            "recycle_loop": False,
            "exp_num": "final_pilot",
            'square': False,
            'render_scale': 10.0, 
            'brightness_contrast': 0.2,
            'auto_back_plane_color': True,
        },
        "separate_variations": {
            "tunnel_width": [1.5, 2.0, 2.5, 3.0],
            "tunnel_height": [1.5, 2.0, 2.5, 3.0],
            "tunnel_depth": [400, 600, 800, 1000],
        },
    },
    "fade_sweep": {
        "description": "Fade distance variations with different marker styles.",
        "variable_spec": {
            "fade_to_back": [True],
            "fade_to_back_start": [5.0, 20.0, 40.0],
            "fade_to_back_end": [150.0, 250.0, 400.0],
            "depth_markers": ["shaded", "both"],
        },
    },
    "exp1_3": {
        "description": "Experiment 1 width/height sweep across durations.",
        "base_updates": {
            "depth_markers": "shaded",
            "renderer_backend": "software",
            "shaded": True,
            "recycle_loop": False,
            'square': False,
            'render_scale': 10.0, 
            'brightness_contrast': 0.2,
            'auto_back_plane_color': True,
        },
        "variable_spec": {
            "tunnel_width": [1.5, 2.0, 2.5, 3.0],
            "duration": [4.0, 6.0, 8.0, 10.0],
            "exp_num": ["1"],
        },
    },
    "exp2_4": {
        "description": "Experiment 2 segment length and speed sweep.",
        "variable_spec": {
            "segment_length": [2.0, 3.0, 4.0, 5.0],
            "speed": [1.0, 2.0, 3.0, 4.0],
            "duration": [5.0],
            "exp_num": ["2"],
        },
    },
}

RESOLUTION_PRESETS: Dict[str, tuple[int, int]] = {
    "3840 x 2160 (4K)": (3840, 2160),
    "2560 x 1440 (QHD)": (2560, 1440),
    "1920 x 1080 (FHD)": (1920, 1080),
    "1280 x 720 (HD)": (1280, 720),
    "960 x 960 (Square)": (960, 960),
}


def coerce_value(text: str) -> Any:
    """Convert a user-provided token into bool/number/str."""

    cleaned = text.strip()
    lowered = cleaned.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit()):
            return int(cleaned)
        return float(cleaned)
    except ValueError:
        return cleaned


def parse_list(text: str) -> List[Any]:
    return [coerce_value(part) for part in text.split(",") if part.strip()]


def parse_value_or_list(raw: str, caster):
    """Convert a string into a cast value or list of cast values."""

    text = raw.strip()

    def apply_cast(value: Any) -> Any:
        try:
            return caster(value)
        except TypeError:
            return caster(str(value))

    # Try JSON-style list input first (e.g., "[1, 2, 3]").
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [apply_cast(item) for item in parsed]
    except json.JSONDecodeError:
        pass

    # Fallback: comma-separated list without brackets.
    if "," in text:
        parts = [part.strip() for part in text.split(",") if part.strip()]
        return [apply_cast(part) for part in parts]

    # Single value
    return apply_cast(text)


def prompt_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        choice = input(f"{prompt}{suffix}").strip().lower()
        if not choice:
            return default
        if choice in {"y", "yes"}:
            return True
        if choice in {"n", "no"}:
            return False
        print("Please enter 'y' or 'n'.")


def prompt_overrides() -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}
    print("\nOptional: override default parameters for all videos.")
    print("Enter key=value pairs separated by commas (e.g., duration=6, fps=30) or press Enter to skip.")
    raw = input("Overrides: ").strip()
    if not raw:
        return overrides
    pairs = [pair.strip() for pair in raw.split(",") if pair.strip()]
    for pair in pairs:
        if "=" not in pair:
            print(f"Skipping '{pair}' (missing '='.)")
            continue
        key, value = pair.split("=", 1)
        overrides[key.strip()] = coerce_value(value)
    return overrides


def prompt_resolution(params: Dict[str, Any], updates: Dict[str, Any]) -> None:
    """Prompt for a resolution preset or custom width/height."""

    default_res = tuple(params.get("resolution", default_params().get("resolution", (1920, 1080))))
    default_label = next(
        (name for name, res in RESOLUTION_PRESETS.items() if res == default_res),
        f"{default_res[0]} x {default_res[1]}",
    )

    print("\nVideo resolution presets:")
    for idx, name in enumerate(RESOLUTION_PRESETS, start=1):
        print(f"  {idx}. {name}")
    print("  c. Custom")

    choice = input(f"Resolution choice [{default_label}]: ").strip().lower()
    if not choice:
        return

    if choice in {"c", "custom"}:
        try:
            width = int(input("  Width (px): ").strip())
            height = int(input("  Height (px): ").strip())
        except ValueError:
            print("Invalid custom resolution; keeping defaults.")
            return
        selected = (width, height)
    else:
        try:
            idx = int(choice)
            names = list(RESOLUTION_PRESETS.keys())
            selected = RESOLUTION_PRESETS[names[idx - 1]]
        except (ValueError, IndexError):
            print("Invalid preset selection; keeping defaults.")
            return

    updates["resolution"] = selected
    square_flag = updates.get("square", params.get("square", False))
    effective = compute_render_resolution({**params, **updates, "square": square_flag, "resolution": selected})
    print(
        f"Selected resolution: {selected[0]} x {selected[1]} (square={square_flag})"
    )
    if effective != selected:
        print(f"Effective render resolution with square mode: {effective[0]} x {effective[1]}")


def prompt_manual_parameters(base_params: Dict[str, Any]) -> Dict[str, Any]:
    """Interactively update parameters that are exposed in the GUI."""

    base_params.setdefault("show_camera_marker", True)
    base_params.setdefault("motion_blur", False)
    base_params.setdefault("blur_samples", 5)

    updates: Dict[str, Any] = {}

    def ask_numeric(key: str, label: str, caster):
        default = base_params.get(key)
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return
        try:
            updates[key] = parse_value_or_list(raw, caster)
        except (ValueError, TypeError):
            print(f"Invalid value for {label}; keeping {default}.")

    def ask_choice(key: str, label: str, options: List[str]):
        default = str(base_params.get(key))
        raw = input(f"{label} ({'/'.join(options)}) [{default}]: ").strip()
        if not raw:
            return
        if raw not in options:
            print(f"Invalid option. Please choose from {options}.")
            return
        updates[key] = raw

    def ask_bool(key: str, label: str):
        default = bool(base_params.get(key))
        updates[key] = prompt_yes_no(label, default=default)

    print("\nManual parameter entry (press Enter to keep defaults).")
    prompt_resolution(base_params, updates)
    ask_numeric("tunnel_width", "Tunnel width", float)
    ask_numeric("tunnel_height", "Tunnel height", float)
    ask_numeric("segment_length", "Segment length", float)
    ask_numeric("duration", "Duration (seconds)", float)
    ask_numeric("speed", "Speed", float)
    ask_numeric("fps", "Frames per second", float)
    ask_numeric("fovy", "Vertical field of view (degrees)", float)
    ask_numeric("tunnel_depth", "Tunnel depth", float)
    ask_numeric("back_plane_color", "Back plane color (0-1)", float)
    ask_bool("auto_back_plane_color", "Auto-adjust back plane color?")
    ask_numeric("brightness_contrast", "Contrast", float)
    ask_choice("depth_markers", "Depth markers", ["none", "wireframe", "shaded", "both"])
    ask_choice("color_mode", "Color mode", ["color", "bw"])
    ask_choice("segment_brightness", "Brightness pattern", ["alternating", "random", "monotonous"])
    ask_choice(
        "color_palette",
        "Color palette",
        ["orange", "cyan", "lime", "pink", "white", "red", "blue", "yellow", "teal", "peach"],
    )
    ask_choice("renderer_backend", "Renderer backend", ["software", "moderngl"])
    ask_bool("shaded", "Enable shading (lighting)?")
    ask_bool("recycle_loop", "Recycle loop?")
    ask_bool("square", "Force square aspect?")
    ask_bool("fade_to_back", "Fade to back?")
    ask_numeric("fade_to_back_start", "Fade start distance", float)
    ask_numeric("fade_to_back_end", "Fade end distance", float)
    ask_numeric("temporal_oversample", "Temporal oversample", int)

    # GUI-only extras with sensible defaults when missing.
    ask_bool("show_camera_marker", "Show camera marker?")
    ask_bool("motion_blur", "Enable motion blur?")
    ask_numeric("blur_samples", "Blur samples", int)

    return updates


def run_preset() -> None:
    print("\nAvailable presets:")
    for index, (name, data) in enumerate(PRESETS.items(), start=1):
        print(f"  {index}. {name} — {data['description']}")
    selection = input("Choose a preset by number or name: ").strip()

    chosen_key = None
    if selection.isdigit():
        idx = int(selection) - 1
        if 0 <= idx < len(PRESETS):
            chosen_key = list(PRESETS.keys())[idx]
    elif selection in PRESETS:
        chosen_key = selection

    if not chosen_key:
        print("Invalid selection; aborting.")
        return

    preset = PRESETS[chosen_key]
    variation_keys = (
        preset.get("variable_spec") or preset.get("separate_variations") or preset.get("custom_param_list") or {}
    )
    print(f"\nRunning preset '{chosen_key}' with {len(variation_keys)} varying parameter groups.")

    base_params = default_params()
    base_params.update(preset.get("base_updates", {}))

    if prompt_yes_no("Do you want to specify other parameters manually?", default=False):
        manual_updates = prompt_manual_parameters(base_params)
        base_params.update(manual_updates)

    apply_palette_color(base_params)

    overrides = prompt_overrides()
    if overrides:
        print("Applying overrides to defaults for every combination...")
        base_params.update(overrides)
        apply_palette_color(base_params)

    if "custom_param_list" in preset:
        param_list = [
            {**base_params, **params}
            for params in preset["custom_param_list"]
        ]
    elif "separate_variations" in preset:
        param_list = []
        for name, values in preset["separate_variations"].items():
            for value in values:
                params = base_params.copy()
                params[name] = value
                param_list.append(params)
    else:
        param_list = generate_param_combinations(base_params, preset["variable_spec"])
    for params in param_list:
        apply_palette_color(params)

    print(f"Prepared {len(param_list)} parameter combinations from preset.")
    if prompt_yes_no("Proceed with batch export?", default=True):
        prepare_batch_videos(custom_param_list=param_list)
    else:
        print("Aborted by user.")


def build_param_grid() -> None:
    base_params = default_params()
    if prompt_yes_no("Do you want to specify other parameters manually?", default=False):
        manual_updates = prompt_manual_parameters(base_params)
        base_params.update(manual_updates)

    apply_palette_color(base_params)

    overrides = prompt_overrides()
    if overrides:
        print("Applying overrides to defaults for every combination...")
        base_params.update(overrides)
        apply_palette_color(base_params)

    while True:
        try:
            count = int(input("\nHow many parameters do you want to vary? ").strip())
            if count < 0:
                raise ValueError
            break
        except ValueError:
            print("Please enter a non-negative integer.")

    variable_spec: Dict[str, List[Any]] = {}
    for idx in range(count):
        name = input(f"Parameter {idx + 1} name: ").strip()
        values = parse_list(input(f"Values for '{name}' (comma separated): "))
        variable_spec[name] = values

    if not variable_spec:
        print("No varying parameters provided. Exporting a single video with defaults/overrides.")
        param_list = [base_params]
    else:
        param_list = generate_param_combinations(base_params, variable_spec)
        print(f"\nPrepared {len(param_list)} parameter combinations.")

    for params in param_list:
        apply_palette_color(params)

    if prompt_yes_no("Proceed with batch export?", default=True):
        prepare_batch_videos(custom_param_list=param_list)
    else:
        print("Aborted by user.")


def run_single_video() -> None:
    params = default_params()
    if prompt_yes_no("Do you want to specify other parameters manually?", default=False):
        manual_updates = prompt_manual_parameters(params)
        params.update(manual_updates)

    overrides = prompt_overrides()
    params.update(overrides)
    apply_palette_color(params)
    print("\nExporting with the following parameters:")
    for key, value in sorted(params.items()):
        print(f"  {key}: {value}")
    if prompt_yes_no("Proceed with single export?", default=True):
        prepare_batch_videos(custom_param_list=[params])
    else:
        print("Aborted by user.")


def run_json_input() -> None:
    print("\nPaste a JSON string describing either a list of parameter dicts or a variable-spec dict.")
    raw = input("JSON: ").strip()
    if not raw:
        print("No input provided.")
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}")
        return

    if isinstance(data, dict) and not any(isinstance(v, list) for v in data.values()):
        print("Dictionary with non-list values detected; wrapping as single parameter set.")
        apply_palette_color(data)
        prepare_batch_videos(custom_param_list=[data])
    elif isinstance(data, dict):
        print("Interpreting dictionary as variable-spec combinations.")
        base_params = default_params()
        apply_palette_color(base_params)
        params = generate_param_combinations(base_params, data)
        for param in params:
            apply_palette_color(param)
        prepare_batch_videos(custom_param_list=params)
    elif isinstance(data, list):
        print(f"Loaded {len(data)} parameter dictionaries from JSON list.")
        for params in data:
            apply_palette_color(params)
        prepare_batch_videos(custom_param_list=data)
    else:
        print("Unsupported JSON structure; please provide a dict or list.")


def main() -> None:
    print("""
==============================
Batch Exporter Interactive Mode
==============================
Choose one of the options below to generate videos.
    """)
    menu = {
        "1": ("Run a preset batch", run_preset),
        "2": ("Build a custom parameter grid", build_param_grid),
        "3": ("Export a single video with overrides", run_single_video),
        "4": ("Provide raw JSON parameters", run_json_input),
        "q": ("Quit", None),
    }

    for key, (label, _) in menu.items():
        print(f"  {key}. {label}")

    choice = input("\nSelection: ").strip().lower()
    action = menu.get(choice)
    if not action:
        print("Unrecognized choice; exiting.")
        return

    _, handler = action
    if handler:
        handler()
    else:
        print("Exiting without running batch exporter.")


if __name__ == "__main__":
    main()