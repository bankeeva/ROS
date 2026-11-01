#!/usr/bin/env python3
import hashlib
import json
import os
import statistics
import sys
import time as wall_time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.clock import Clock as WallClock
from rclpy.clock import ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from rclpy.time import Time
from rosgraph_msgs.msg import Clock as ClockMessage
from tf2_ros import Buffer, TransformListener

MINIMUM_TF_AVAILABILITY = 0.95
MAXIMUM_MEDIAN_COVARIANCE_M2 = 0.25
MINIMUM_AMCL_SAMPLES = 10


def xy_covariance_sum(covariance) -> float:
    return float(covariance[0]) + float(covariance[7])


def median_covariance(values) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def window_bounds(t0_ns: int, warmup_s: float, duration_s: float) -> tuple[int, int]:
    start_ns = t0_ns + int(round(warmup_s * 1e9))
    end_ns = start_ns + int(round(duration_s * 1e9))
    return start_ns, end_ns


class LocalizationMetrics(Node):
    def __init__(self) -> None:
        super().__init__(
            "localization_metrics",
            parameter_overrides=[Parameter("use_sim_time", value=True)],
        )
        self.declare_parameter("output_path", "evidence/pr08/localization.json")
        self.declare_parameter("map_yaml", "")
        self.declare_parameter("map_pgm", "")
        self.declare_parameter("recording_path", "fixtures/pr07-sensors")
        self.declare_parameter("warmup_s", 10.0)
        self.declare_parameter("duration_s", 20.0)
        self.declare_parameter("query_rate_hz", 10.0)
        self.declare_parameter("end_silence_s", 3.0)
        self.declare_parameter("defect_before_frame", "chassis")
        self.declare_parameter("defect_after_frame", "base_link")
        self.declare_parameter(
            "defect_symptom",
            "AMCL не публикует map->odom, потому что преобразование base_link->chassis отсутствует",
        )
        self.declare_parameter("shutdown_after_write", True)

        self._output_path = str(self.get_parameter("output_path").value)
        self._map_yaml = str(self.get_parameter("map_yaml").value)
        self._map_pgm = str(self.get_parameter("map_pgm").value)
        self._recording_path = str(self.get_parameter("recording_path").value)
        self._warmup_s = float(self.get_parameter("warmup_s").value)
        self._duration_s = float(self.get_parameter("duration_s").value)
        self._rate_hz = float(self.get_parameter("query_rate_hz").value)
        self._end_silence_s = float(self.get_parameter("end_silence_s").value)
        self._defect_before = str(self.get_parameter("defect_before_frame").value)
        self._defect_after = str(self.get_parameter("defect_after_frame").value)
        self._defect_symptom = str(self.get_parameter("defect_symptom").value)
        self._shutdown_after_write = bool(
            self.get_parameter("shutdown_after_write").value
        )

        self._step_ns = int(round(1e9 / self._rate_hz))
        self._expected_queries = int(round(self._duration_s * self._rate_hz))

        self._t0_ns = None
        self._window_start_ns = None
        self._window_end_ns = None
        self._next_query_ns = None
        self._last_clock_ns = None
        self._last_clock_wall = None
        self._last_query_ns = None
        self._queries_total = 0
        self._queries_successful = 0
        self._rate_misses = 0
        self._last_tf_error = ""
        self._covariances = []
        self._window_done = False
        self._written = False
        self._ok = False

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

        clock_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=ReliabilityPolicy.BEST_EFFORT,
        )
        pose_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=100,
            reliability=ReliabilityPolicy.BEST_EFFORT,
        )
        self.create_subscription(ClockMessage, "/clock", self._on_clock, clock_qos)
        self.create_subscription(
            PoseWithCovarianceStamped, "/amcl_pose", self._on_amcl_pose, pose_qos
        )

        self._wall_clock = WallClock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(1.0, self._watchdog, clock=self._wall_clock)

        self.get_logger().info(
            "localization_metrics: warmup=%.1f s, window=%.1f s, rate=%.1f Hz, "
            "output=%s"
            % (self._warmup_s, self._duration_s, self._rate_hz, self._output_path)
        )

    def _on_clock(self, message: ClockMessage) -> None:
        now_ns = message.clock.sec * 1_000_000_000 + message.clock.nanosec
        self._last_clock_ns = now_ns
        self._last_clock_wall = wall_time.monotonic()

        if self._t0_ns is None:
            self._t0_ns = now_ns
            self._window_start_ns, self._window_end_ns = window_bounds(
                self._t0_ns, self._warmup_s, self._duration_s
            )
            self._next_query_ns = self._window_start_ns
            self.get_logger().info(
                "t0=%.3f s, window=[%.3f, %.3f)"
                % (
                    self._t0_ns / 1e9,
                    self._window_start_ns / 1e9,
                    self._window_end_ns / 1e9,
                )
            )

        if now_ns < self._window_start_ns:
            return
        if self._window_done:
            return
        self._run_schedule(now_ns)

    def _run_schedule(self, now_ns: int) -> None:
        max_lag_ns = int(0.15e9)
        while (
            self._next_query_ns < self._window_end_ns
            and now_ns - self._next_query_ns > max_lag_ns
        ):
            self._queries_total += 1
            self._rate_misses += 1
            self._next_query_ns += self._step_ns

        if self._next_query_ns >= self._window_end_ns:
            self._finish_window()
            return
        if now_ns < self._next_query_ns:
            return
        if (
            self._last_query_ns is not None
            and now_ns - self._last_query_ns < int(0.05e9)
        ):
            self._queries_total += 1
            self._rate_misses += 1
            self._next_query_ns += self._step_ns
            return

        self._queries_total += 1
        try:
            self._tf_buffer.lookup_transform("map", "odom", Time())
            self._queries_successful += 1
        except Exception as error:
            self._last_tf_error = str(error)
            self.get_logger().warning(
                "map->odom lookup failed: %s" % self._last_tf_error,
                throttle_duration_sec=1.0,
            )
        self._last_query_ns = now_ns
        self._next_query_ns += self._step_ns

        if self._next_query_ns >= self._window_end_ns:
            self._finish_window()

    def _on_amcl_pose(self, message: PoseWithCovarianceStamped) -> None:
        if self._window_start_ns is None:
            return
        stamp_ns = message.header.stamp.sec * 1_000_000_000
        stamp_ns += message.header.stamp.nanosec
        if self._window_start_ns <= stamp_ns < self._window_end_ns:
            self._covariances.append(xy_covariance_sum(message.pose.covariance))

    def _finish_window(self) -> None:
        if self._window_done:
            return
        self._window_done = True
        self.get_logger().info(
            "window finished: tf=%d/%d, amcl_pose=%d, rate_misses=%d"
            % (
                self._queries_successful,
                self._queries_total,
                len(self._covariances),
                self._rate_misses,
            )
        )

    def _watchdog(self) -> None:
        if self._written or not self._window_done:
            return
        if self._last_clock_wall is None:
            return
        if wall_time.monotonic() - self._last_clock_wall < self._end_silence_s:
            return
        self.write_result()

    def write_result(self) -> bool:
        if self._written:
            return self._ok
        if not self._window_done or self._last_clock_ns is None:
            self.get_logger().error("measurement window is incomplete")
            return False
        if not self._map_yaml or not self._map_pgm:
            self.get_logger().error("map_yaml and map_pgm parameters are required")
            return False
        try:
            map_yaml_sha = sha256_file(self._map_yaml)
            map_pgm_sha = sha256_file(self._map_pgm)
        except OSError as error:
            self.get_logger().error("cannot read map files: %s" % error)
            return False

        total = self._queries_total
        successful = self._queries_successful
        availability = successful / total if total > 0 else 0.0
        samples = len(self._covariances)
        median = median_covariance(self._covariances)
        recording_duration = (self._last_clock_ns - self._t0_ns) / 1e9

        payload = {
            "schema_version": 1,
            "map_sha256": {"map.yaml": map_yaml_sha, "map.pgm": map_pgm_sha},
            "recording": {
                "path": self._recording_path,
                "duration_s": recording_duration,
            },
            "initial_pose": {"x_m": 0.0, "y_m": 0.0, "yaw_rad": 0.0},
            "evaluation": {
                "warmup_s": self._warmup_s,
                "duration_s": self._duration_s,
                "tf_queries_total": total,
                "tf_queries_successful": successful,
                "tf_availability": availability,
                "amcl_pose_samples": samples,
                "median_xy_covariance_m2": median,
            },
            "defect": {
                "before_base_frame_id": self._defect_before,
                "after_base_frame_id": self._defect_after,
                "observed_symptom": self._defect_symptom,
            },
        }

        output_path = os.path.abspath(self._output_path)
        directory = os.path.dirname(output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary_path = output_path + ".tmp"
        with open(temporary_path, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary_path, output_path)

        self._written = True
        self._ok = (
            total >= self._expected_queries
            and availability >= MINIMUM_TF_AVAILABILITY
            and samples >= MINIMUM_AMCL_SAMPLES
            and median <= MAXIMUM_MEDIAN_COVARIANCE_M2
            and recording_duration >= self._warmup_s + self._duration_s
        )

        self.get_logger().info(
            "result: tf=%d/%d (%.4f), amcl_pose=%d, median=%.6f m^2, "
            "recording=%.3f s, status=%s"
            % (
                successful,
                total,
                availability,
                samples,
                median,
                recording_duration,
                "ok" if self._ok else "failed",
            )
        )
        if self._rate_misses > 0:
            self.get_logger().warning(
                "query rate was not maintained: %d steps missed" % self._rate_misses
            )
        if self._shutdown_after_write and rclpy.ok():
            rclpy.shutdown()
        return self._ok


def main(args=None) -> int:
    rclpy.init(args=args)
    node = LocalizationMetrics()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node._window_done and not node._written:
            node.write_result()
        code = 0 if node._written and node._ok else 1
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return code


if __name__ == "__main__":
    sys.exit(main())
