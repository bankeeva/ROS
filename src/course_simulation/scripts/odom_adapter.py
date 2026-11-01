#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import rclpy
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from tf2_ros import TransformBroadcaster

from course_simulation.kinematics import (
    SOURCE_PREFIX,
    normalize_odometry,
    odometry_transform,
)


class OdomAdapter(Node):
    def __init__(self) -> None:
        super().__init__("odom_adapter")

        self.declare_parameter("input_topic", "/vehicle/odom_gz")
        self.declare_parameter("output_topic", "/vehicle/odom")
        self.declare_parameter("source_prefix", SOURCE_PREFIX)

        self._input_topic = self.get_parameter("input_topic").value
        self._output_topic = self.get_parameter("output_topic").value
        self._source_prefix = self.get_parameter("source_prefix").value

        odometry_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        tf_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=100,
            reliability=ReliabilityPolicy.RELIABLE,
        )

        self._odom_publisher = self.create_publisher(
            Odometry, self._output_topic, odometry_qos
        )
        self._tf_broadcaster = TransformBroadcaster(self, qos=tf_qos)
        self._odom_subscription = self.create_subscription(
            Odometry, self._input_topic, self._on_odometry, odometry_qos
        )

        self._normalized_count = 0
        self._rejected_count = 0

        self.get_logger().info(
            "odom_adapter: %s (%s/odom, %s/base_link) -> %s (odom, base_link), "
            "single owner of dynamic tf odom->base_link"
            % (
                self._input_topic,
                self._source_prefix,
                self._source_prefix,
                self._output_topic,
            )
        )

    def _on_odometry(self, message: Odometry) -> None:
        result = normalize_odometry(message, self._source_prefix)
        if result.message is None:
            self._rejected_count += 1
            self.get_logger().warning(
                "rejected odometry (%s) with frames %r -> %r; nothing published"
                % (result.reason, result.source_frame, result.source_child_frame),
                throttle_duration_sec=1.0,
            )
            return

        self._odom_publisher.publish(result.message)
        self._tf_broadcaster.sendTransform(odometry_transform(result.message))
        self._normalized_count += 1


def main(args=None) -> None:
    rclpy.init(args=args)

    def _shutdown(signum, _frame):
        rclpy.try_shutdown()
        os._exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    node = OdomAdapter()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception:
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
