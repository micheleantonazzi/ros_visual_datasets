# ROS Visual Datasets
This repository contains some ROS nodes to publish visual datasets (like Scannet) inside the ROS infrastructure. 

## Usage

This reposiory can be simply downloaded inside a ROS workspace and built using catkin. (ROS noetic on Ubuntu 20.04 has been tested but other ROS 1 versions can be used instead.)

### Docker
We provide also a docker container where ROS Noetic and CUDA are configured and ready to use.
The container configure the ROS workspace to build the ROS nodes resposible to publish the desidered dataset.

To run the code with ROS using the container we provide a script with 4 commands:
* `start`: Starts the ROS Docker environment by executing the specified Docker Compose file.
* `stop`: Stops and removes the Docker containers defined in the Docker Compose file.
* `restart`: Stops, rebuilds, and restarts the Docker containers.
* `build`: Builds the Docker containers defined in the Docker Compose file.

To use the script just run `./use_container.sh <command>`. At first, build the container, then start it.

We suggest to use VS code with the "Dev Container" extension installed. When the container is running, typing `ctrl+shift+p` and seach the command `Attach to running container`. This procedure will open a VS code windows inside the running container for development.
Once inside the container, build the package simply running `catkin build` inside the workspace directory.

## Dataset preparation

Remember to run the dataset setup ouside the docker container otherwise all the files should not be accessible from your account.
To fix this issue run `sudo chmod a+rwx <folder>`.

### Scannet

At first request the official script to download Scannet [here](https://github.com/ScanNet/ScanNet/tree/master) and copy it inside a python file in  [datasets_setup_scripts/scannet/official_download_script.py](./datasets_setup_scripts/scannet/official_download_script.py)`

* Select the directory in which you want to download the dataset with and setup an environment variable typing `export DATA_ROOT=~/myfiles/scannet`
* Download the labels with `python3 datasets_setup_scripts/scannet/official_download_script.py --label_map -o ${DATA_ROOT}`
* Download the data of the scenes you are interested. To do this, modify the script [download_scenes.py](./datasets_setup_scripts/scannet/download_scenes.py) changing the `scenes` and then run `python3 datasets_setup_scripts/scannet/download_scenes.py`.
* Extract all the sensor data for each of the downloaded scenes. To do this, modify the `scene` variable inside the file [extract_data.py](./datasets_setup_scripts/scannet/extract_data.py) and the run `python3 datasets_setup_scripts/scannet/extract_data.py`. After the extraction, the `.sens` file is removed for space saving. You can disable this changing a bool inside the script.
* Convert the labels to the Nyu40 or Nyu13 encoding using the following command `python3 datasets_setup_scripts/scannet/scannet_preprocess.py --labels_format nyu40` (`nyu13` if you want to change the labels format). This scripts generated the image with the semantic labels and the semantic colors.

### Scannetpp
* Prepare a Python 3.10 virtual environment
* Install the requirements by typing `pip3 install -r datasets_setup_scripts/scannetpp/toolkit/requirements.txt`
* Install pytorch3d typing `pip install --no-index --no-cache-dir pytorch3d -f https://dl.fbaipublicfiles.com/pytorch3d/packaging/wheels/py310_cu116_pyt1131/download.html`
* Install additional requirements  `pip3 install omegaconf hydra-core wandb codetiming`
* Modify the configurations inside `/home/antonazzi/myfiles/repositories/ros_visual_datasets/datasets_setup_scripts/scannetpp/toolkit/semantic/configs/rasterize.yaml`