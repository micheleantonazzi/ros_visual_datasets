import argparse
import copy
import csv
import cv2
import json
import numpy as np
import os

from tqdm import tqdm

from utils import SCANNET_COLORS_NYU40, SCANNET_COLORS_NYU13




def load_scannet_nyu40_mapping(path):
    mapping = {}
    with open(os.path.join(path, 'scannetv2-labels.combined.tsv')) as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter='\t')
        for i, line in enumerate(tsvreader):
            if i == 0:
                continue
            scannet_id, nyu40id = int(line[0]), int(line[4])
            mapping[scannet_id] = nyu40id
    return mapping


def load_scannet_nyu13_mapping(path):
    mapping = {}
    with open(os.path.join(path, 'scannetv2-labels.combined.tsv')) as tsvfile:
        tsvreader = csv.reader(tsvfile, delimiter='\t')
        for i, line in enumerate(tsvreader):
            if i == 0:
                continue
            scannet_id, nyu40id = int(line[0]), int(line[5])
            mapping[scannet_id] = nyu40id
    return mapping


parser = argparse.ArgumentParser(
    description=
    "Run neural graphics primitives testbed with additional configuration & output options"
)

parser.add_argument("--scene_folder", type=str, default="")
parser.add_argument("--labels_format", type=str, default='nyu40', choices=['nyu40', 'nyu13'])
args = parser.parse_args()
basedir = args.scene_folder

print(f"processing folder: {basedir}")

# Step for generating training images
step = 1

frame_ids = os.listdir(os.path.join(basedir, 'color'))
frame_ids = [int(os.path.splitext(frame)[0]) for frame in frame_ids]
frame_ids = sorted(frame_ids)

intrinsic_file = os.path.join(basedir, "intrinsic/intrinsic_color.txt")
intrinsic = np.loadtxt(intrinsic_file)
print("intrinsic parameters:")
print(intrinsic)

imgs = []
poses = []


if args.labels_format == 'nyu40':
    label_mapping_nyu = load_scannet_nyu40_mapping(basedir)
    os.makedirs(os.path.join(basedir, 'label_nyu40'), exist_ok=True)
    os.makedirs(os.path.join(basedir, 'label_nyu40_colored'), exist_ok=True)
    colors = SCANNET_COLORS_NYU40
        
else:
    label_mapping_nyu = load_scannet_nyu13_mapping(basedir)
    os.makedirs(os.path.join(basedir, 'label_nyu13'), exist_ok=True)
    os.makedirs(os.path.join(basedir, 'label_nyu13_colored'), exist_ok=True)
    colors = SCANNET_COLORS_NYU13


for frame_id in tqdm(frame_ids):
    file_name_label = os.path.join(basedir, 'label-filt',
                                               '%d.png' % frame_id)
    semantic = cv2.imread(file_name_label, cv2.IMREAD_UNCHANGED)
    semantic_colored = np.zeros((semantic.shape[0], semantic.shape[1], 3))
    semantic_copy = copy.deepcopy(semantic)
    for scan_id, nyu_id in label_mapping_nyu.items():
        semantic[semantic_copy == scan_id] = nyu_id
    
    for i in range(len(colors)):
        semantic_colored[semantic == i, :3] = colors[i][::-1]

    semantic = semantic.astype(np.uint8)
    
    cv2.imwrite(os.path.join(basedir, f'label_{args.labels_format}', '%d.png' % frame_id), semantic)
    cv2.imwrite(os.path.join(basedir, f'label_{args.labels_format}_colored', '%d.png' % frame_id), semantic_colored)

