import os
import subprocess
from time import sleep
import argparse

scenes = [f'scene{i:04}_00' for i in range(0, 1)]

parser = argparse.ArgumentParser(
    description=
    "Run neural graphics primitives testbed with additional configuration & output options"
)

parser.add_argument("--labels_format", type=str, default='nyu40', choices=['nyu40', 'nyu13'])
args = parser.parse_args()
labels_format = args.labels_format

for scene in scenes:
    sleep(10)
    command = f"python3 datasets_setup_scripts/scannet/scannet_preprocess_utils.py --scene_folder ${{DATA_ROOT}}/scans/{scene} --labels_format {labels_format}"

    print(f'Extract data for {scene}', command)
    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE)

    process.wait()

    if process.returncode == 0:
        print(f"Extraction for {scene} completed successfully.")
    else:
        print(f"Extraction for {scene} failed with error {process.returncode}")