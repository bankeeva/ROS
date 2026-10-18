#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from turtlesim_msgs.msg import Pose


class PoseRelay(Node):
    def __init__(self):
        super().__init__("pose_relay")

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            durability=DurabilityPolicy.VOLATILE,
        )

        out_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            durability=DurabilityPolicy.VOLATILE,
        )

        self.sub = self.create_subscription(
            Pose, "turtle1/pose", self.on_pose, sensor_qos
        )
        self.pub = self.create_publisher(Pose, "sensor_pose", out_qos)

        self.get_logger().info("pose_relay started (best_effort out)")

    def on_pose(self, msg):
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = PoseRelay()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
