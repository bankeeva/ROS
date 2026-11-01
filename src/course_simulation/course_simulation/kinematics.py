from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry


WHEEL_BASE_M = 0.8
MAX_SPEED_MPS = 1.2
MAX_STEERING_RAD = 0.45
COMMAND_TIMEOUT_S = 0.25
SOURCE_PREFIX = "course_ackermann"
NORMALIZED_ODOM_FRAME = "odom"
NORMALIZED_BASE_FRAME = "base_link"


@dataclass(frozen=True)
class DriveEvaluation:
    linear_x: float
    angular_z: float
    valid: bool
    reason: str


@dataclass(frozen=True)
class OdometryNormalization:
    message: Optional[Odometry]
    reason: str
    source_frame: str = ""
    source_child_frame: str = ""


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def steering_to_angular(
    speed: float,
    steering_angle: float,
    wheel_base: float = WHEEL_BASE_M,
) -> float:
    return speed * math.tan(steering_angle) / wheel_base


def evaluate_drive(
    speed: float,
    steering_angle: float,
    stamp_ns: int,
    now_ns: int,
    max_speed: float = MAX_SPEED_MPS,
    max_steering: float = MAX_STEERING_RAD,
    wheel_base: float = WHEEL_BASE_M,
    timeout_s: float = COMMAND_TIMEOUT_S,
) -> DriveEvaluation:
    if not math.isfinite(speed):
        return DriveEvaluation(0.0, 0.0, False, "non_finite_speed")
    if not math.isfinite(steering_angle):
        return DriveEvaluation(0.0, 0.0, False, "non_finite_steering")

    age_s = (now_ns - stamp_ns) / 1e9
    if age_s > timeout_s:
        return DriveEvaluation(0.0, 0.0, False, f"stale_stamp:{age_s:.3f}s")
    if -age_s > timeout_s:
        return DriveEvaluation(0.0, 0.0, False, f"future_stamp:{-age_s:.3f}s")

    speed = clamp(speed, 0.0, max_speed)
    steering_angle = clamp(steering_angle, -max_steering, max_steering)
    return DriveEvaluation(
        linear_x=speed,
        angular_z=steering_to_angular(speed, steering_angle, wheel_base),
        valid=True,
        reason="ok",
    )


def twist_from_evaluation(evaluation: DriveEvaluation) -> Twist:
    twist = Twist()
    twist.linear.x = float(evaluation.linear_x)
    twist.angular.z = float(evaluation.angular_z)
    return twist


def zero_twist() -> Twist:
    return Twist()


def command_is_stale(
    last_stamp_ns: Optional[int],
    now_ns: int,
    timeout_s: float = COMMAND_TIMEOUT_S,
) -> bool:
    if last_stamp_ns is None:
        return False
    return (now_ns - last_stamp_ns) / 1e9 > timeout_s


def normalize_odometry(
    message: Odometry,
    prefix: str = SOURCE_PREFIX,
) -> OdometryNormalization:
    source_frame = message.header.frame_id
    source_child = message.child_frame_id
    expected_frame = f"{prefix}/odom"
    expected_child = f"{prefix}/base_link"

    if source_frame != expected_frame:
        return OdometryNormalization(
            None, f"unexpected_frame:{source_frame}", source_frame, source_child
        )
    if source_child != expected_child:
        return OdometryNormalization(
            None, f"unexpected_child_frame:{source_child}", source_frame, source_child
        )

    pose = message.pose.pose
    twist = message.twist.twist
    values = (
        pose.position.x,
        pose.position.y,
        pose.position.z,
        pose.orientation.x,
        pose.orientation.y,
        pose.orientation.z,
        pose.orientation.w,
        twist.linear.x,
        twist.linear.y,
        twist.linear.z,
        twist.angular.x,
        twist.angular.y,
        twist.angular.z,
        *message.pose.covariance,
        *message.twist.covariance,
    )
    if not all(math.isfinite(value) for value in values):
        return OdometryNormalization(
            None, "non_finite", source_frame, source_child
        )

    normalized = Odometry()
    normalized.header.stamp = message.header.stamp
    normalized.header.frame_id = NORMALIZED_ODOM_FRAME
    normalized.child_frame_id = NORMALIZED_BASE_FRAME
    normalized.pose = message.pose
    normalized.twist = message.twist
    return OdometryNormalization(
        normalized, "ok", source_frame, source_child
    )


def odometry_transform(message: Odometry) -> TransformStamped:
    transform = TransformStamped()
    transform.header.stamp = message.header.stamp
    transform.header.frame_id = NORMALIZED_ODOM_FRAME
    transform.child_frame_id = NORMALIZED_BASE_FRAME
    transform.transform.translation.x = message.pose.pose.position.x
    transform.transform.translation.y = message.pose.pose.position.y
    transform.transform.translation.z = message.pose.pose.position.z
    transform.transform.rotation = message.pose.pose.orientation
    return transform
