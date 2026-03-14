import os
import itertools
import json
from datetime import datetime
from tunnel_module import (
    default_params,
    generate_filename,
    export_video,
)
import cv2
import numpy as np
import csv


def generate_param_combinations(base_params, variable_specs):
    keys = list(variable_specs.keys())
    value_lists = list(variable_specs.values())
    combinations = list(itertools.product(*value_lists))

    param_list = []
    for combo in combinations:
        new_params = base_params.copy()
        for k, v in zip(keys, combo):
            new_params[k] = v
        param_list.append(new_params)

    return param_list


def prepare_batch_videos(variable_instructions=None, custom_param_list=None):
    import subprocess
    import shutil

    base_params = default_params()

    folder_name = input("Enter folder name for batch output: ").strip()
    out_folder = os.path.join(os.getcwd(), folder_name)
    os.makedirs(out_folder, exist_ok=True)

    csv_rows = []

    if custom_param_list:
        param_list = custom_param_list
    elif variable_instructions:
        param_list = generate_param_combinations(base_params, variable_instructions)
    else:
        print("Error: You must provide either custom_param_list or variable_instructions.")
        return

    print(f"Starting batch export of {len(param_list)} videos...")

    for i, params in enumerate(param_list):
        filename = generate_filename(params)
        try:
            final_path, _ = export_video(params, out_folder)
        except Exception as e:
            print(f"❌ Failed to export {filename}: {e}")
            continue

        csv_rows.append([
            f"{folder_name}/{filename}",
            params['tunnel_width'],
            params['tunnel_height'],
            params['segment_length'],
            params['tunnel_depth'],
            params['duration'],
            params['speed'],
            params.get('recycle_loop', False),
            params['color_mode'],
            params['segment_brightness'],
            params['depth_markers'],
            params.get('fade_to_back', False),
            params.get('fade_to_back_start', 10.0),
            params.get('fade_to_back_end', 400.0),
        ])

        print(f"[{i+1}/{len(param_list)}] ✅ Saved {os.path.basename(final_path)}")

    print(f"✅ Batch export complete. Files saved in {out_folder}")

    if csv_rows:
        csv_path = os.path.join(out_folder, 'stimuli.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'video_path',
                'width_1',
                'height_1',
                'segment_length',
                'tunnel_depth',
                'duration',
                'speed',
                'recycle_loop',
                'color_mode',
                'segment_brightness',
                'depth_markers',
                'fade_to_back',
                'fade_to_back_start',
                'fade_to_back_end'
            ])
            writer.writerows(csv_rows)
        print(f"✅ CSV manifest saved to {csv_path}")



# #usage for pilot study: 4 widths × 4 heights = 16 conditions
# if __name__ == '__main__':
#     variable_spec = {
#         'tunnel_width': [1.0, 1.5, 2.0, 2.5],
#         'tunnel_height': [1.0, 1.5, 2.0, 2.5],
#         'exp_num': ['pilot']
#     }
#     prepare_batch_videos(variable_instructions=variable_spec)

# #usage
if __name__ == '__main__':
    import sys
    # from batch_exporter import prepare_batch_videos  # adjust import if needed

    # Check for special keyword like "pilot" or custom grid
    if len(sys.argv) > 1 and sys.argv[1] == "pilot":
        variable_spec = {
            'tunnel_width': [1.0, 1.5, 2.0, 2.5],
            'tunnel_height': [1.0, 1.5, 2.0, 2.5],
            'exp_num': ['pilot']
        }
        prepare_batch_videos(variable_instructions=variable_spec)
    elif len(sys.argv) > 1 and sys.argv[1] == "pilotdepth":    
        variable_spec = {
            'tunnel_depth': [100, 200, 300, 400],
            'recycle_loop': [True, False],
            'exp_num': ['pilot']
        }
        prepare_batch_videos(variable_instructions=variable_spec)
    elif len(sys.argv) > 1 and sys.argv[1] == "pilotinfinity":
        variable_spec = {
            'tunnel_width': [1.0, 1.5, 2.0, 2.5],
            'tunnel_height': [1.0, 2.0],
            'tunnel_depth': [100, 200, 1000],  # fixed depth for pilot
            'recycle_loop': [True, False],
            'duration': [5.0],  # fixed stimulus duration
            'exp_num': ['pilot']
        }
        prepare_batch_videos(variable_instructions=variable_spec)
    elif len(sys.argv) > 1 and sys.argv[1] == "final_pilot":
        base_params = default_params()
        base_params.update({
            'depth_markers': 'shaded',
            'renderer_backend': 'software',
            'shaded': True,
            'duration': [5.0],  # fixed stimulus duration
            'recycle_loop': False,
            'exp_num': 'final_pilot',
        })

        separate_variations = {
            'tunnel_width': [1.0, 1.5, 2.0, 2.5],
            'tunnel_height': [1.0, 1.5, 2.0, 2.5],
            'tunnel_depth': [100, 200, 300, 400],
        }

        param_list = []
        for name, values in separate_variations.items():
            for value in values:
                params = base_params.copy()
                params[name] = value
                param_list.append(params)

        prepare_batch_videos(custom_param_list=param_list)
    elif len(sys.argv) > 1 and sys.argv[1] == "fade_sweep":
        variable_spec = {
            'fade_to_back': [True],
            'fade_to_back_start': [5.0, 20.0, 40.0],
            'fade_to_back_end': [150.0, 250.0, 400.0],
            'depth_markers': ['shaded', 'both'],
        }
        print("Running fade sweep batch: varying fade distances and marker styles.")
        prepare_batch_videos(variable_instructions=variable_spec)
    elif len(sys.argv) > 1 and sys.argv[1] == "exp1_3":
        variable_spec = {
            'tunnel_width': [1.0, 1.5, 2.0, 2.5],  # or 'tunnel_height' depending on pilot results
            'duration': [4.0, 6.0, 8.0, 10.0],
            'exp_num': ['1']
        }
        prepare_batch_videos(variable_instructions=variable_spec)
    elif len(sys.argv) > 1 and sys.argv[1] == "exp2_4":
        variable_spec = {
            'segment_length': [2.0, 3.0, 4.0, 5.0],
            'speed': [1.0, 2.0, 3.0, 4.0],
            'duration': [5.0],  # fixed stimulus duration
            'exp_num': ['2']
        }
        prepare_batch_videos(variable_instructions=variable_spec)
    else:  # Default case, prompt for custom parameters
        print("No specific experiment selected. Please provide custom parameters.")
        custom_params = input("Enter custom parameters as JSON string: ")
        try:
            custom_param_list = json.loads(custom_params)
            prepare_batch_videos(custom_param_list=custom_param_list)
        except json.JSONDecodeError:
            print("Invalid JSON format. Please try again.")