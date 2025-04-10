import time
import rclpy
from rclpy.node import Node
import numpy as np
from std_msgs.msg import Float32
from geometry_msgs.msg import PoseStamped
from joint_state_recorder import JointStatesRecorder
import panda_py
from rclpy.clock import Clock


class JointStatesRecorderPanda(JointStatesRecorder):
    def __init__(self, folder_name: str, config: dict):
        super().__init__(folder_name, 7, "/hday/rt_franka/joint_state")
        self._pykeyboard.stop()
        hostname = config["hostname"]
        username = config["username"]
        password = config["password"]
        self.desk = panda_py.Desk(hostname, username, password)
        self.desk.listen(self._on_press_panda)
        self.desk._listening = True

        self.vibration_pub = self.create_publisher(Float32, "/haptic_feedback", 10)
        self.pose_subsciber = self.create_subscription(
            PoseStamped, "/hday/rt_franka/ef_pose", self._pose_callback, 10
        )

        self._last_time_pressed = time.time()
        self._pose = np.zeros(7)
        # self.set_K = dynamic_reconfigure.client.Client(
        #     "/dynamic_reconfigure_compliance_param_node", config_callback=None
        # )
        # self.set_K.update_configuration({"translational_stiffness_X": 0})
        # self.set_K.update_configuration({"translational_stiffness_Y": 0})
        # self.set_K.update_configuration({"translational_stiffness_Z": 0})
        # self.set_K.update_configuration({"rotational_stiffness_X": 0})
        # self.set_K.update_configuration({"rotational_stiffness_Y": 0})
        # self.set_K.update_configuration({"rotational_stiffness_Z": 0})

    def _pose_callback(self, pose: PoseStamped) -> None:
        self._pose = np.array(
            [
                pose.pose.position.x,
                pose.pose.position.y,
                pose.pose.position.z,
                pose.pose.orientation.w,
                pose.pose.orientation.x,
                pose.pose.orientation.y,
                pose.pose.orientation.z,
            ]
        )

    def vibrate(self, duration=0.2):
        msg = Float32()
        msg.data = float(duration)
        self.vibration_pub.publish(msg)

    def _on_press_panda(self, event: dict) -> None:
        time_since_last_press = time.time() - self._last_time_pressed
        if time_since_last_press < 0.6:
            return
        self._last_time_pressed = time.time()

        if "check" in event and event["check"]:
            self._data[self.hole_name()].append(self._positions)
            self._data[f"{self.hole_name()}_pose"].append(self._pose)

            self.log(
                f"Added data point for {self.hole_name()} with value {self._positions}"
            )
            if len(self._data[self.hole_name()]) >= 30:
                self.vibrate(duration=0.5)
                print("test")
            else:
                self.vibrate()
        elif "down" in event and event["down"]:
            self._data[self.hole_name()] = self._data[self.hole_name()][0:-1]
            self.log(f"Deleted data point for {self.hole_name()}")
            self.vibrate()
        elif "cross" in event and event["cross"]:
            self.desk._listening = False
            self.log("Saving data to file and exiting")
            self.save_data()
            self.vibrate()
            print("Wait for terminal to shut down.....")
            rclpy.shutdown()
            return
        elif "circle" in event and event["circle"]:
            self._active_hole = (self._active_hole + 1) % 3
            self.log(f"Switched to hole {self._active_hole}")
            self.vibrate(duration=1)
        else:
            self.log("Unknown key pressed")
        self.print_info()
        self.print_circle_with_number(self.hole_name()[-1])

    def print_info(self):
        self.log("Press 'check' to add a data point")
        self.log("Press 'down' to delete the last data point")
        self.log("Press 'o' to switch between holes")
        self.log("Press 'x' to save the data and quit.")

    def print_circle_with_number(self, number):
        self.log(f"Saved joint for hole 0:")
        self.log_joint_length(len(self._data["hole_0"]))
        self.log(f"Saved joint for 1: {len(self._data['hole_1'])}")
        self.log_joint_length(len(self._data["hole_1"]))
        self.log(f"Saved joint for 2: {len(self._data['hole_2'])}")
        self.log_joint_length(len(self._data["hole_2"]))
        self.log(f"Active hole is green:")

        number = int(number)
        if number == 0:
            color1, color2, color3 = 32, 0, 0
        elif number == 1:
            color1, color2, color3 = 0, 32, 0
        elif number == 2:
            color1, color2, color3 = 0, 0, 32

        square = f"""
            \033[{color1}m████████████   \033[{color2}m████████████   \033[{color3}m████████████
            \033[{color1}m█          █   \033[{color2}m█          █   \033[{color3}m█          █
            \033[{color1}m█     {0}    █   \033[{color2}m█     {1}    █   \033[{color3}m█     {2}    █
            \033[{color1}m█          █   \033[{color2}m█          █   \033[{color3}m█          █
            \033[{color1}m████████████   \033[{color2}m████████████   \033[{color3}m████████████ 
            \033[0m
        """

        print(square)
