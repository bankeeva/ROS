#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import rclpy
from ackermann_msgs.msg import AckermannDriveStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

CYCLE_S = 8.0
PHASES = (
    (1.5, 0.30, 0.00),
    (2.5, 0.30, 0.15),
    (3.5, 0.00, 0.00),
    (5.0, 0.30, 0.00),
    (6.0, 0.30, -0.15),
    (CYCLE_S, 0.00, 0.00),
)


class TestDriveSource(Node):
    def __init__(self) -> None:
        super().__init__("test_drive_source")
        self.declare_parameter("topic", "/drive/safe")
        self.declare_parameter("publish_rate", 10.0)
        self.declare_parameter("mode", "pattern")
        self.declare_parameter("speed", 0.30)
        self.declare_parameter("steering", 0.0)

        self._topic = self.get_parameter("topic").value
        rate = float(self.get_parameter("publish_rate").value)
        self._mode = str(self.get_parameter("mode").value).strip().lower()
        self._fixed_speed = float(self.get_parameter("speed").value)
        self._fixed_steering = float(self.get_parameter("steering").value)

        command_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self._publisher = self.create_publisher(
            AckermannDriveStamped, self._topic, command_qos
        )
        self._start_ns = None
        self._phase_index = None
        self.create_timer(1.0 / rate, self._publish, clock=self.get_clock())

        self.get_logger().info(
            "test_drive_source: mode=%s on %s at %.1f Hz with simulation "
            "stamps (stand-in for the PR11 supervisor)"
            % (self._mode, self._topic, rate)
        )
        if self._mode == "fixed":
            self.get_logger().info(
                "fixed command: speed=%.2f m/s steering=%.2f rad"
                % (self._fixed_speed, self._fixed_steering)
            )

    def _publish(self) -> None:
        now = self.get_clock().now()
        now_ns = now.nanoseconds
        if self._start_ns is None or now_ns < self._start_ns:
            self._start_ns = now_ns
        elapsed = (now_ns - self._start_ns) / 1e9
        phase = elapsed % CYCLE_S

        if self._mode == "fixed":
            speed = self._fixed_speed
            steering = self._fixed_steering
        else:
            speed = 0.0
            steering = 0.0
            for index, (phase_end, phase_speed, phase_steering) in enumerate(PHASES):
                if phase < phase_end:
                    speed, steering = phase_speed, phase_steering
                    if self._phase_index != index:
                        self._phase_index = index
                        self.get_logger().info(
                            "pattern phase %d: speed=%.2f m/s steering=%.2f rad"
                            % (index, speed, steering)
                        )
                    break

        message = AckermannDriveStamped()
        message.header.stamp = now.to_msg()
        message.header.frame_id = "base_link"
        message.drive.speed = speed
        message.drive.steering_angle = steering
        message.drive.acceleration = 0.0
        message.drive.jerk = 0.0
        self._publisher.publish(message)


def main(args=None) -> None:
    rclpy.init(args=args)

    def _shutdown(signum, _frame):
        rclpy.try_shutdown()
        os._exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    node = TestDriveSource()
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
