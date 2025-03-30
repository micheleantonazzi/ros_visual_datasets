#!/usr/bin/python3
# license removed for brevity
import rospy
from std_msgs.msg import String, Header
import cv2
import os
import tf2_ros
import numpy as np
import sensor_msgs.point_cloud2 as point_cloud2
from sensor_msgs.msg import Image, CameraInfo, PointCloud2, PointField
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
from cv_bridge import CvBridge
import tf_conversions
import copy
from collections import OrderedDict

labels_to_rgb = OrderedDict([
    ("unlabeled", (0, 0, 0)),
    ("wall", (174, 199, 232)),
    ("floor", (152, 223, 138)),
    ("cabinet", (31, 119, 180)),
    ("bed", (255, 187, 120)),
    ("chair", (188, 189, 34)),
    ("sofa", (140, 86, 75)),
    ("table", (255, 152, 150)),
    ("door", (214, 39, 40)),
    ("window", (197, 176, 213)),
    ("bookshelf", (148, 103, 189)),
    ("picture", (196, 156, 148)),
    ("counter", (23, 190, 207)),
    ("blinds", (178, 76, 76)),
    ("desk", (247, 182, 210)),
    ("shelves", (66, 188, 102)),
    ("curtain", (219, 219, 141)),
    ("dresser", (140, 57, 197)),
    ("pillow", (202, 185, 52)),
    ("mirror", (51, 176, 203)),
    ("floormat", (200, 54, 131)),
    ("clothes", (92, 193, 61)),
    ("ceiling", (78, 71, 183)),
    ("books", (172, 114, 82)),
    ("refrigerator", (255, 127, 14)),
    ("television", (91, 163, 138)),
    ("paper", (153, 98, 156)),
    ("towel", (140, 153, 101)),
    ("showercurtain", (158, 218, 229)),
    ("box", (100, 125, 154)),
    ("whiteboard", (178, 127, 135)),
    ("person", (120, 185, 128)),
    ("nightstand", (146, 111, 194)),
    ("toilet", (44, 160, 44)),
    ("sink", (112, 128, 144)),
    ("lamp", (96, 207, 209)),
    ("bathtub", (227, 119, 194)),
    ("bag", (213, 92, 176)),
    ("otherstructure", (94, 106, 211)),
    ("otherfurniture", (82, 84, 163)),
    ("otherprop", (100, 85, 144)),
])

class_to_rgb = [v for v in labels_to_rgb.values()]


def get_camera_info(scannet_folder, scene_id, W_unscaled, H_unscaled, W, H, type):
    K = np.loadtxt(os.path.join(scannet_folder, 'scans', scene_id, 'intrinsic', f'intrinsic_{type}.txt')).astype(float)
    
    scale_x = W / W_unscaled
    scale_y = H / H_unscaled

    K[0, 0] = K[0, 0] * scale_x  # fx
    K[1, 1] = K[1, 1] * scale_y  # fy
    K[0, 2] = K[0, 2] * scale_x  # cx
    K[1, 2] = K[1, 2] * scale_y  # cy

    return K 

def read_pose_file(file_path):
    file = open(file_path, 'r')
    lines = file.readlines()
    pose_matrix = []
    for l in lines:
        line = l.rstrip('\n').split(' ')
        line = np.array(line).astype(float).reshape(4).tolist()
        pose_matrix.append(line)
    
    return np.array(pose_matrix).astype(float).reshape(4, 4)

def scale_image(image, W, H):

    H_original, W_original = image.shape[:2]
    
    
    if W_original != W or H_original != H:
        image = cv2.resize(image, (W, H), interpolation=cv2.INTER_NEAREST)
    
    return image

def create_point_cloud(depth_raw, W_depth, H_depth, K_depth, scale=1000):
    h, w = np.mgrid[0: H_depth, 0: W_depth]
    z = depth_raw / scale
    x = (w - K_depth[0, 2]) * z / K_depth[0, 0] # x = (w - cx) * z / fx
    y = (h - K_depth[1, 2]) * z / K_depth[1, 1] # y = (h - cy) * z / fy
    point_cloud_raw = np.dstack((x, y, z)).reshape(-1, 3)
    return point_cloud_raw

def publish_all_topics(frequency, scene_id, first_message_number, scannet_folder, label_folder, label_colored_folder,
                       W_color, H_color,
                       W_depth, H_depth):
    
    publisher_image = rospy.Publisher('camera/color/image_raw', Image, queue_size=10)
    publisher_image_depth = rospy.Publisher('camera/depth/image_raw', Image, queue_size=10)
    publisher_image_semantic = rospy.Publisher('camera/semantic/image_raw', Image, queue_size=10)
    publisher_image_semantic_colored = rospy.Publisher('camera/semantic/image_colored', Image, queue_size=10)
    publisher_camera_color_info = rospy.Publisher('camera/color/camera_info', CameraInfo, queue_size=10)
    publisher_camera_depth_info = rospy.Publisher('camera/depth/camera_info', CameraInfo, queue_size=10)
    publisher_point_cloud = rospy.Publisher('camera/depth/points', PointCloud2, queue_size=10)

    rospy.init_node('scannet_to_ros')
    rate = rospy.Rate(frequency) 

    bridge = CvBridge()
    files = os.listdir(os.path.join(scannet_folder, 'scans', scene_id, 'color'))
    transform_broadcaster = tf2_ros.TransformBroadcaster()    

    # Define camera info message
    [H_unscaled_color, W_unscaled_color] = cv2.imread(os.path.join(scannet_folder, 'scans', scene_id, 'color', f'0.jpg')).shape[0:2]
    [H_unscaled_depth, W_unscaled_depth] = cv2.imread(os.path.join(scannet_folder, 'scans', scene_id, 'depth', f'0.png')).shape[0:2]

    #     [fx  0 cx]
    # K = [ 0 fy cy]
    #     [ 0  0  1]
    K_color = get_camera_info(scannet_folder, scene_id, 
                                                W_unscaled=W_unscaled_color, H_unscaled=H_unscaled_color, 
                                                W=W_color, H=H_color, type='color') 
    K_depth = get_camera_info(scannet_folder, scene_id, 
                                                W_unscaled=W_unscaled_depth, H_unscaled=H_unscaled_depth, 
                                                W=W_depth, H=H_depth, type='depth') 
    step = 1
    if frequency == 15:
        step = 2
    elif frequency == 10:
        step = 3
    while not rospy.is_shutdown():
        for num in range(0, len(files), step):

            current_time = rospy.Time.now()
            # Camera color info message
            camera_info_color_message = CameraInfo()
            camera_info_color_message.header.stamp = current_time
            camera_info_color_message.width = W_color
            camera_info_color_message.height = H_color
            camera_info_color_message.K = K_color[0:3, 0:3].flatten()
            camera_info_color_message.R = K_color[:3, :3].flatten()
            camera_info_color_message.P = K_color[:3, :4].flatten()
            camera_info_color_message.distortion_model = "plumb_bob"
            camera_info_color_message.header.frame_id = '/camera_rgb_link'

            # Camera depth info message
            camera_info_depth_message = CameraInfo()
            camera_info_depth_message.header.stamp = current_time
            camera_info_depth_message.width = W_depth
            camera_info_depth_message.height = H_depth
            camera_info_depth_message.K = K_depth[0:3, 0:3].flatten().tolist()
            camera_info_depth_message.R = K_depth[:3, :3].flatten()
            camera_info_depth_message.P = K_depth[:3, :4].flatten()
            camera_info_depth_message.distortion_model = "plumb_bob"
            camera_info_depth_message.header.frame_id = '/camera_depth_link'

            #Depth
            transform_camera_depth_message = TransformStamped()
            transform_camera_depth_message.header.stamp = rospy.Time.now()
            transform_camera_depth_message.header.frame_id = '/camera_link'
            transform_camera_depth_message.child_frame_id = '/camera_depth_link'
            transform_camera_depth_message.transform.rotation.x = 0
            transform_camera_depth_message.transform.rotation.y = 0
            transform_camera_depth_message.transform.rotation.z = 0
            transform_camera_depth_message.transform.rotation.w = 1
            
            # Color
            transform_camera_color_message = TransformStamped()
            transform_camera_color_message.header.stamp = rospy.Time.now()
            transform_camera_color_message.header.frame_id = '/camera_link'
            transform_camera_color_message.child_frame_id = '/camera_color_link'
            transform_camera_color_message.transform.rotation.x = 0
            transform_camera_color_message.transform.rotation.y = 0
            transform_camera_color_message.transform.rotation.z = 0
            transform_camera_color_message.transform.rotation.w = 1
                        
            # Load pose
            pose_matrix = read_pose_file(os.path.join(scannet_folder, 'scans', scene_id, 'pose', f'{num}.txt'))
            camera_transform_message = TransformStamped() 
            camera_transform_message.header.stamp = current_time
            camera_transform_message.header.frame_id = '/map'
            camera_transform_message.child_frame_id = '/camera_link'
            camera_transform_message.transform.translation.x = pose_matrix[0, 3]
            camera_transform_message.transform.translation.y = pose_matrix[1, 3]
            camera_transform_message.transform.translation.z = pose_matrix[2, 3]

            rotation_quaternion = tf_conversions.transformations.quaternion_from_matrix(pose_matrix)
            camera_transform_message.transform.rotation.x = rotation_quaternion[0]
            camera_transform_message.transform.rotation.y = rotation_quaternion[1]
            camera_transform_message.transform.rotation.z = rotation_quaternion[2]
            camera_transform_message.transform.rotation.w = rotation_quaternion[3]

            # Load image 
            image_raw = cv2.imread(os.path.join(scannet_folder, 'scans', scene_id, 'color', f'{num}.jpg'))
            image_message_header = Header()
            image_message_header.stamp = current_time
            image_message_header.frame_id = num
            image_message_header.frame_id = 'camera_rgb_link'
            image_raw = scale_image(image=image_raw, W=W_depth, H=H_depth)
            image_message = bridge.cv2_to_imgmsg(image_raw, encoding='bgr8', header=image_message_header)
            
            # Load depth image
            depth_raw = cv2.imread(os.path.join(scannet_folder, 'scans', scene_id, 'depth', f'{num}.png'), cv2.IMREAD_UNCHANGED).astype(np.float32)
            depth_raw = scale_image(image=depth_raw, W=W_depth, H=H_depth)
            image_depth_message_header = Header()
            image_depth_message_header.frame_id = num
            image_depth_message_header.stamp = current_time
            image_depth_message_header.frame_id = 'camera_depth_link'
            image_depth_message = bridge.cv2_to_imgmsg(depth_raw.astype(np.uint16), encoding='16UC1', header=image_depth_message_header)
            
            # Load semantic label
            image_semantic = cv2.imread(os.path.join(scannet_folder, 'scans', scene_id, label_folder, f'{num}.png'), cv2.IMREAD_UNCHANGED)
            image_semantic_colored = cv2.cvtColor(cv2.imread(os.path.join(scannet_folder, 'scans', scene_id, label_colored_folder, f'{num}.png')), cv2.COLOR_BGR2RGB)
            
            image_semantic_colored = image_semantic_colored.astype(np.uint8)
            image_semantic_message_header = Header()
            image_semantic_message_header.frame_id = num
            image_semantic_message_header.stamp = current_time
            image_semantic_message_header.frame_id = 'camera_semantic_link'
            image_semantic_message_colored = bridge.cv2_to_imgmsg(image_semantic_colored, encoding="rgb8", header=image_semantic_message_header)
            image_semantic_message_header = Header()
            image_semantic_message_header.frame_id = num
            image_semantic_message_header.stamp = current_time
            image_semantic_message_header.frame_id = 'camera_semantic_link'
            image_semantic_message = bridge.cv2_to_imgmsg(image_semantic, header=image_semantic_message_header)
            
            # Publish all topics
            transform_broadcaster.sendTransform(camera_transform_message)
            transform_broadcaster.sendTransform(transform_camera_color_message)
            transform_broadcaster.sendTransform(transform_camera_depth_message)
            publisher_image.publish(image_message)
            publisher_camera_color_info.publish(camera_info_color_message)
            publisher_image_depth.publish(image_depth_message)
            publisher_camera_depth_info.publish(camera_info_depth_message)
            publisher_image_semantic.publish(image_semantic_message)
            publisher_image_semantic_colored.publish(image_semantic_message_colored)

            #publisher_point_cloud.publish(point_cloud_message)
            rate.sleep()

if __name__ == '__main__':
    label_folder = rospy.get_param('/scannet_to_ros/label_folder', default='label_nyu40')
    label_colored_folder = rospy.get_param('/scannet_to_ros/label_colored_folder', default='label_nyu40_colored')

    frequency = rospy.get_param('/scannet_to_ros/frequency', default=30)
    scene_id = rospy.get_param("/scannet_to_ros/scene_id", default='scene0000_00')
    first_message_number = rospy.get_param("/scannet_to_ros/first_message_number", default=0)
    scannet_folder = rospy.get_param("/scannet_to_ros/scannet_folder", default='/root/scannet')

    W_depth = rospy.get_param("/scannet_to_ros/W_depth", default=640)
    H_depth = rospy.get_param("/scannet_to_ros/H_depth", default=480)

    if frequency != 30 and frequency != 15 and frequency != 10:
        raise ValueError("The frequency (Hz) must be one of the following: 30, 15, or 10!!!")

    W_color = W_depth
    H_color = H_depth
    try:
        publish_all_topics(frequency, scene_id, first_message_number, scannet_folder, label_folder, label_colored_folder, W_color, H_color, W_depth, H_depth)
    except rospy.ROSInterruptException:
        pass