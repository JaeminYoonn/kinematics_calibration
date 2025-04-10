#!/usr/bin/env python3
import yaml

from joint_state_recorder_xarm6 import JointStatesRecorderXArm6
import os
import argparse
import rclpy


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description="Run the parameter optimizer")
    argument_parser.add_argument(
        "--save_folder_name",
        "-o",
        help="file name which you want to save",
    )

    args = argument_parser.parse_args()
    save_folder_name = args.save_folder_name

    absolute_path = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    data_folder = os.path.join(absolute_path, "data", "holiday_xarm6", save_folder_name)
    if data_folder and not os.path.exists(data_folder):
        os.makedirs(data_folder)

    rclpy.init()
    node = JointStatesRecorderXArm6(data_folder)
    try:
        while rclpy.ok() and not node._exit_mode:
            rclpy.spin_once(node, timeout_sec=0.1)
    except:
        pass
        # traceback.print_exc()
    finally:
        node.destroy_node()
        rclpy.shutdown()
