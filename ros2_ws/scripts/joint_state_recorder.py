import os
import rclpy
from rclpy.node import Node
import numpy as np
import pynput
from sensor_msgs.msg import JointState
import threading


class JointStatesRecorder(Node):
    def __init__(self, folder_name: str, dof: int, topic_name: str):
        super().__init__("joint_states_recorder")
        self._joint_states_sub = self.create_subscription(
            JointState, topic_name, self.joint_states_callback, 10
        )

        self._data = {"hole_0": [], "hole_1": [], "hole_2": []}
        self._dof = dof
        self._positions = np.zeros(self._dof)
        self._active_hole = 0
        # self._pykeyboard = pynput.keyboard.Listener(on_press=self.on_press)
        # self._pykeyboard.start()

        self._pykeyboard_listener_thread = threading.Thread(
            target=self.start_keyboard_listener
        )
        self._pykeyboard_listener_thread.daemon = True
        self._pykeyboard_listener_thread.start()

        self._exit_mode = False

        self._folder_name = folder_name
        if os.path.exists(folder_name):
            self.log(f"Folder {self._folder_name} already exists.")
            if len(os.listdir(folder_name)) != 0:
                self.read_data()
            else:
                self._data = {
                    "hole_0": [],
                    "hole_1": [],
                    "hole_2": [],
                    "hole_0_pose": [],
                    "hole_1_pose": [],
                    "hole_2_pose": [],
                }

        else:
            self.log(f"Creating folder {self._folder_name}")
            os.makedirs(self._folder_name, exist_ok=True)
            self._data = {
                "hole_0": [],
                "hole_1": [],
                "hole_2": [],
                "hole_0_pose": [],
                "hole_1_pose": [],
                "hole_2_pose": [],
            }

        self.print_info()
        self.print_status()

    def start_keyboard_listener(self):
        self._listener = pynput.keyboard.Listener(on_press=self.on_press)
        self._listener.start()  # 리스너 시작

    def read_data(self):
        for file_name in os.listdir(self._folder_name):
            hole_name = file_name.split(".")[0]
            file_path = os.path.join(self._folder_name, file_name)
            data = np.loadtxt(file_path, delimiter=",")
            self._data[hole_name] = data.tolist()

    def print_info(self):
        self.log("Press 'a' to add a data point")
        self.log("Press 'd' to delete the last data point")
        self.log("Press 's' to switch between holes")
        self.log("Press 'q' to save the data and quit.")

    def log(self, msg: str):
        print(msg)

    def hole_name(self):
        return f"hole_{self._active_hole}"

    def on_press(self, key):

        try:
            # Check if the key has the 'char' attribute
            if hasattr(key, "char") and key.char:
                # Add the current position to the data if the space key is pressed
                if key.char == "a":
                    self._data[self.hole_name()].append(self._positions)
                    self.log(
                        f"Addded data point for {self.hole_name()} with value {self._positions}"
                    )
                elif key.char == "d":
                    self._data[self.hole_name()] = self._data[self.hole_name()][0:-1]
                    self.log(f"Deleted data point for {self.hole_name()}")
                elif key.char == "q":
                    self.log("Saving data to file and exiting")
                    self.save_data()
                    print("Finished recording data")
                    rclpy.shutdown()
                elif key.char == "s":
                    self._active_hole = (self._active_hole + 1) % 3
                    self.log(f"Switched to hole {self._active_hole}")
                elif key.char == "i":
                    self.print_info()
                self.print_info()
                self.print_status()
            else:
                # Handle special keys
                if key == pynput.keyboard.Key.esc:
                    self.log("Esc key pressed, shutting down.")
                    self._listener.stop()
                    self._exit_mode = True
                    # rclpy.shutdown()
                    # exit(0)
        except AttributeError:
            # Handle the case where 'key' does not have a 'char' attribute
            self.log(f"Special key pressed: {key}")

    def shutdown_and_exit(self):
        # ROS가 초기화되지 않았다면 초기화
        if not rclpy.ok():
            rclpy.init()

        # 리스너를 중지하고, rclpy 종료 및 프로그램 종료
        if self._listener:
            self._listener.stop()  # 리스너 종료
        rclpy.shutdown()  # ROS 종료
        print("ROS shutdown completed.")
        exit(0)  # 프로세스 종료

    def print_status(self):
        self.log(f"Saved joint for hole 0:")
        self.log_joint_length(len(self._data["hole_0"]))
        self.log(f"Saved joint for 1: {len(self._data['hole_1'])}")
        self.log_joint_length(len(self._data["hole_1"]))
        self.log(f"Saved joint for 2: {len(self._data['hole_2'])}")
        self.log_joint_length(len(self._data["hole_2"]))
        self.log(f"Active hole is green:")
        self.print_circle_with_number(self.hole_name()[-1])

    def log_joint_length(self, length):
        # Calculate the length of the array
        # length = len(self._data['hole_0'])

        # Create an ASCII block representation of the length
        block = "█" * length  # Each '█' represents one unit in the length

        # Log the message with the ASCII block and the value at the end
        self.log(f"{block} ({length})")

    def print_circle_with_number(self, number):
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

        self.log(square)

    def save_data(self):
        for hole_name, data in self._data.items():
            file_name = os.path.join(self._folder_name, f"{hole_name}.csv")
            np.savetxt(file_name, np.array(data), delimiter=",")
            self.log(f"Saved {len(self._data[hole_name])} points for {hole_name}")

    def joint_states_callback(self, msg: JointState):
        self._positions = np.array(msg.position)[0 : self._dof]
