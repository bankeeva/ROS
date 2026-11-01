#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import rclpy
from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from course_simulation.kinematics import (
    COMMAND_TIMEOUT_S,
    MAX_SPEED_MPS,
    MAX_STEERING_RAD,
    WHEEL_BASE_M,
    command_is_stale,
    evaluate_drive,
    twist_from_evaluation,
    zero_twist,
)


def stamp_to_ns(stamp) -> int:
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


class AckermannAdapter(Node):
    def __init__(self) -> None:
        super().__init__("ackermann_adapter")

        self.declare_parameter("input_topic", "/drive/safe")
        self.declare_parameter("output_topic", "/vehicle/gz_cmd_vel")
        self.declare_parameter("max_speed", MAX_SPEED_MPS)
        self.declare_parameter("max_steering", MAX_STEERING_RAD)
        self.declare_parameter("wheel_base", WHEEL_BASE_M)
        self.declare_parameter("command_timeout", COMMAND_TIMEOUT_S)
        self.declare_parameter("watchdog_period", 0.1)

        self._input_topic = self.get_parameter("input_topic").value
        self._output_topic = self.get_parameter("output_topic").value
        self._max_speed = float(self.get_parameter("max_speed").value)
        self._max_steering = float(self.get_parameter("max_steering").value)
        self._wheel_base = float(self.get_parameter("wheel_base").value)
        self._timeout = float(self.get_parameter("command_timeout").value)
        watchdog_period = float(self.get_parameter("watchdog_period").value)

        command_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self._twist_publisher = self.create_publisher(
            Twist, self._output_topic, command_qos
        )
        self._drive_subscription = self.create_subscription(
            AckermannDriveStamped, self._input_topic, self._on_drive, command_qos
        )

        self._last_command_ns = None
        self._stopped = True
        self._accepted = 0
        self._rejected = 0

        self.create_timer(
            watchdog_period, self._watchdog, clock=self.get_clock()
        )

        self.get_logger().info(
            "ackermann_adapter: %s -> %s; wheel_base=%.2f m, "
            "v<=%.2f m/s, |delta|<=%.2f rad, timeout=%.2f s"
            % (
                self._input_topic,
                self._output_topic,
                self._wheel_base,
                self._max_speed,
                self._max_steering,
                self._timeout,
            )
        )

    def _on_drive(self, message: AckermannDriveStamped) -> None:
        now_ns = self.get_clock().now().nanoseconds
        stamp_ns = stamp_to_ns(message.header.stamp)
        evaluation = evaluate_drive(
            message.drive.speed,
            message.drive.steering_angle,
            stamp_ns,
            now_ns,
            max_speed=self._max_speed,
            max_steering=self._max_steering,
            wheel_base=self._wheel_base,
            timeout_s=self._timeout,
        )
        if not evaluation.valid:
            self._rejected += 1
            self.get_logger().warning(
                "rejected drive command (%s): publishing zero Twist, "
                "last command is not repeated" % evaluation.reason,
                throttle_duration_sec=1.0,
            )
            self._publish_stop()
            return

        self._twist_publisher.publish(twist_from_evaluation(evaluation))
        self._accepted += 1
        self._last_command_ns = now_ns
        self._stopped = evaluation.linear_x == 0.0 and evaluation.angular_z == 0.0
        self.get_logger().debug(
            "drive v=%.3f m/s delta=%.3f rad -> linear.x=%.3f angular.z=%.3f"
            % (
                message.drive.speed,
                message.drive.steering_angle,
                evaluation.linear_x,
                evaluation.angular_z,
            )
        )

    def _watchdog(self) -> None:
        if self._stopped:
            return
        now_ns = self.get_clock().now().nanoseconds
        if not command_is_stale(self._last_command_ns, now_ns, self._timeout):
            return
        self.get_logger().warning(
            "command watchdog: no fresh /drive/safe command for more than "
            "%.2f s of simulation time, publishing zero Twist" % self._timeout,
            throttle_duration_sec=1.0,
        )
        self._publish_stop()

    def _publish_stop(self) -> None:
        self._twist_publisher.publish(zero_twist())
        self._last_command_ns = None
        self._stopped = True


def main(args=None) -> None:
    rclpy.init(args=args)

    def _shutdown(signum, _frame):
        rclpy.try_shutdown()
        os._exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    node = AckermannAdapter()
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
