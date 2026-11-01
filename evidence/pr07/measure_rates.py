#!/usr/bin/env python3
import argparse
import json
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image, Imu, LaserScan

SENSOR_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
    reliability=ReliabilityPolicy.BEST_EFFORT,
)
RELIABLE_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
    reliability=ReliabilityPolicy.RELIABLE,
)

TOPICS = {
    "/vehicle/camera/image_raw": (Image, SENSOR_QOS, "camera_link"),
    "/vehicle/scan": (LaserScan, SENSOR_QOS, "lidar_link"),
    "/vehicle/imu": (Imu, SENSOR_QOS, "imu_link"),
    "/vehicle/odom": (Odometry, RELIABLE_QOS, "odom"),
}


class RateMeasurement(Node):
    def __init__(self) -> None:
        super().__init__("pr07_rate_measurement")
        self.set_parameters(
            [Parameter("use_sim_time", Parameter.Type.BOOL, True)]
        )
        self.samples = {topic: [] for topic in TOPICS}
        self.subscriptions_list = []
        for topic, (msg_type, qos, _frame) in TOPICS.items():
            self.subscriptions_list.append(
                self.create_subscription(
                    msg_type,
                    topic,
                    lambda msg, topic=topic: self._on_message(topic, msg),
                    qos,
                )
            )

    def _on_message(self, topic, message) -> None:
        stamp = message.header.stamp
        stamp_ns = int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
        self.samples[topic].append(
            {
                "wall_ns": time.monotonic_ns(),
                "stamp_ns": stamp_ns,
                "frame_id": message.header.frame_id,
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=30.0, help="wall seconds")
    args = parser.parse_args()

    rclpy.init()
    node = RateMeasurement()

    # Wait for the simulation clock before starting the window.
    deadline = time.monotonic() + 60.0
    while node.get_clock().now().nanoseconds == 0 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)

    wall_start_ns = time.monotonic_ns()
    sim_start_ns = node.get_clock().now().nanoseconds
    for topic in node.samples:
        node.samples[topic].clear()

    end = time.monotonic() + args.duration
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.1)

    wall_end_ns = time.monotonic_ns()
    sim_end_ns = node.get_clock().now().nanoseconds

    wall_s = (wall_end_ns - wall_start_ns) / 1e9
    sim_s = (sim_end_ns - sim_start_ns) / 1e9

    report = {
        "window_wall_s": round(wall_s, 3),
        "window_sim_s": round(sim_s, 3),
        "rtf": round(sim_s / wall_s, 3) if wall_s > 0 else None,
        "topics": {},
    }
    for topic, (msg_type, _qos, expected_frame) in TOPICS.items():
        samples = node.samples[topic]
        entry = {
            "type": "%s/msg/%s" % (msg_type.__module__.split(".")[0], msg_type.__name__),
            "count": len(samples),
            "frame_id": samples[-1]["frame_id"] if samples else None,
            "expected_frame": expected_frame,
            "wall_rate_hz": round(len(samples) / wall_s, 2) if wall_s else None,
        }
        if len(samples) >= 2:
            stamps = [sample["stamp_ns"] for sample in samples]
            span_ns = stamps[-1] - stamps[0]
            entry["sim_span_s"] = round(span_ns / 1e9, 3)
            entry["sim_rate_hz"] = round((len(samples) - 1) / (span_ns / 1e9), 2)
            gaps = [
                (stamps[index + 1] - stamps[index]) / 1e9
                for index in range(len(stamps) - 1)
            ]
            entry["sim_gap_min_s"] = round(min(gaps), 4)
            entry["sim_gap_max_s"] = round(max(gaps), 4)
        report["topics"][topic] = entry

    print(json.dumps(report, indent=2, sort_keys=True))
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
