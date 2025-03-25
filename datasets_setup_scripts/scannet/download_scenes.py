import os
import subprocess
import time

# Download the second scene
scenes = [f'scene{i:04}_00' for i in range(2, 3)]

for scene in scenes:
    command = ("python3 datasets_setup_scripts/scannet/official_download_script.py -o ${DATA_ROOT} --id " + scene)
    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE)
    time.sleep(1)
    process.stdin.write(b'\n')
    process.stdin.flush()

    time.sleep(1)
    process.stdin.write(b'\n')
    process.stdin.flush()

    process.wait()


    if process.returncode == 0:
        print(f"Download for {scene} completed successfully.")
    else:
        print(f"Failed to download {scene}. Return code: {process.returncode}")