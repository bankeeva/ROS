import math

import pytest
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

from course_simulation.kinematics import (
    MAX_SPEED_MPS,
    MAX_STEERING_RAD,
    WHEEL_BASE_M,
    clamp,
    command_is_stale,
    evaluate_drive,
    normalize_odometry,
    odometry_transform,
    steering_to_angular,
    twist_from_evaluation,
)

NOW_NS = 1_000_000_000


def _odometry(
    frame_id: str = "course_ackermann/odom",
    child_frame_id: str = "course_ackermann/base_link",
):
    message = Odometry()
    message.header.stamp.sec = 12
    message.header.stamp.nanosec = 345
    message.header.frame_id = frame_id
    message.child_frame_id = child_frame_id
    message.pose.pose.position.x = 1.5
    message.pose.pose.position.y = -0.25
    message.pose.pose.position.z = 0.18
    message.pose.pose.orientation.z = 0.1
    message.pose.pose.orientation.w = 0.9949874371
    message.twist.twist.linear.x = 0.3
    message.twist.twist.angular.z = 0.05
    message.pose.covariance[0] = 0.25
    message.twist.covariance[35] = 1.5
    return message


def test_forward_motion_produces_straight_twist():
    evaluation = evaluate_drive(0.5, 0.0, NOW_NS, NOW_NS)
    assert evaluation.valid
    assert evaluation.reason == "ok"
    assert evaluation.linear_x == pytest.approx(0.5)
    assert evaluation.angular_z == pytest.approx(0.0)
    twist = twist_from_evaluation(evaluation)
    assert twist.linear.x == pytest.approx(0.5)
    assert twist.angular.z == pytest.approx(0.0)


def test_turn_uses_wheel_base_formula():
    evaluation = evaluate_drive(1.0, 0.3, NOW_NS, NOW_NS)
    assert evaluation.valid
    assert evaluation.linear_x == pytest.approx(1.0)
    assert evaluation.angular_z == pytest.approx(math.tan(0.3) / WHEEL_BASE_M)


def test_zero_speed_does_not_rotate_in_place():
    evaluation = evaluate_drive(0.0, 0.4, NOW_NS, NOW_NS)
    assert evaluation.valid
    assert evaluation.linear_x == 0.0
    assert evaluation.angular_z == 0.0
    assert steering_to_angular(0.0, 0.4) == 0.0


def test_speed_and_steering_are_clamped():
    evaluation = evaluate_drive(5.0, 1.0, NOW_NS, NOW_NS)
    assert evaluation.linear_x == pytest.approx(MAX_SPEED_MPS)
    assert evaluation.angular_z == pytest.approx(
        MAX_SPEED_MPS * math.tan(MAX_STEERING_RAD) / WHEEL_BASE_M
    )


def test_negative_speed_is_clamped_to_zero():
    evaluation = evaluate_drive(-1.0, 0.2, NOW_NS, NOW_NS)
    assert evaluation.valid
    assert evaluation.linear_x == 0.0
    assert evaluation.angular_z == 0.0


def test_negative_steering_is_clamped_symmetrically():
    evaluation = evaluate_drive(0.6, -2.0, NOW_NS, NOW_NS)
    assert evaluation.angular_z == pytest.approx(
        0.6 * math.tan(-MAX_STEERING_RAD) / WHEEL_BASE_M
    )


def test_stale_command_is_rejected_with_zero_twist():
    stale_stamp = NOW_NS - int(0.3 * 1e9)
    evaluation = evaluate_drive(0.8, 0.2, stale_stamp, NOW_NS)
    assert not evaluation.valid
    assert evaluation.reason.startswith("stale_stamp")
    assert evaluation.linear_x == 0.0
    assert evaluation.angular_z == 0.0


def test_command_age_equal_to_timeout_is_still_fresh():
    boundary_stamp = NOW_NS - int(0.25 * 1e9)
    evaluation = evaluate_drive(0.8, 0.0, boundary_stamp, NOW_NS)
    assert evaluation.valid


def test_future_stamp_is_rejected():
    evaluation = evaluate_drive(0.8, 0.0, NOW_NS + int(1e9), NOW_NS)
    assert not evaluation.valid
    assert evaluation.reason.startswith("future_stamp")


@pytest.mark.parametrize(
    "speed, steering_angle, reason",
    [
        (math.nan, 0.0, "non_finite_speed"),
        (math.inf, 0.0, "non_finite_speed"),
        (0.5, math.nan, "non_finite_steering"),
        (0.5, -math.inf, "non_finite_steering"),
    ],
)
def test_non_finite_command_is_rejected(speed, steering_angle, reason):
    evaluation = evaluate_drive(speed, steering_angle, NOW_NS, NOW_NS)
    assert not evaluation.valid
    assert evaluation.reason == reason
    assert evaluation.linear_x == 0.0
    assert evaluation.angular_z == 0.0


def test_command_is_stale_helper_for_watchdog():
    assert command_is_stale(None, NOW_NS) is False
    assert command_is_stale(NOW_NS - int(0.1 * 1e9), NOW_NS) is False
    assert command_is_stale(NOW_NS - int(0.3 * 1e9), NOW_NS) is True


def test_clamp_helper():
    assert clamp(2.0, 0.0, 1.2) == 1.2
    assert clamp(-2.0, 0.0, 1.2) == 0.0
    assert clamp(0.5, 0.0, 1.2) == 0.5


def test_odometry_frames_are_normalised_and_data_preserved():
    source = _odometry()
    result = normalize_odometry(source)
    assert result.reason == "ok"
    assert result.message is not None
    assert result.source_frame == "course_ackermann/odom"
    assert result.source_child_frame == "course_ackermann/base_link"
    normalised = result.message
    assert normalised.header.frame_id == "odom"
    assert normalised.child_frame_id == "base_link"
    assert normalised.header.stamp == source.header.stamp
    assert normalised.pose.pose.position.x == pytest.approx(1.5)
    assert normalised.pose.pose.position.y == pytest.approx(-0.25)
    assert normalised.twist.twist.linear.x == pytest.approx(0.3)
    assert normalised.twist.twist.angular.z == pytest.approx(0.05)
    assert normalised.pose.covariance[0] == pytest.approx(0.25)
    assert normalised.twist.covariance[35] == pytest.approx(1.5)
    assert list(normalised.pose.covariance) == pytest.approx(
        list(source.pose.covariance)
    )
    assert list(normalised.twist.covariance) == pytest.approx(
        list(source.twist.covariance)
    )


def test_odometry_with_unknown_prefix_is_rejected():
    result = normalize_odometry(_odometry(frame_id="map/odom"))
    assert result.message is None
    assert result.reason == "unexpected_frame:map/odom"


def test_odometry_with_unexpected_child_frame_is_rejected():
    result = normalize_odometry(_odometry(child_frame_id="course_ackermann/base"))
    assert result.message is None
    assert result.reason.startswith("unexpected_child_frame")


def test_odometry_with_non_finite_pose_is_rejected():
    source = _odometry()
    source.pose.pose.position.x = math.nan
    result = normalize_odometry(source)
    assert result.message is None
    assert result.reason == "non_finite"


def test_odometry_with_non_finite_covariance_is_rejected():
    source = _odometry()
    source.twist.covariance[7] = math.inf
    result = normalize_odometry(source)
    assert result.message is None
    assert result.reason == "non_finite"


def test_transform_matches_odometry_and_keeps_stamp():
    source = _odometry()
    normalised = normalize_odometry(source).message
    transform = odometry_transform(normalised)
    assert transform.header.frame_id == "odom"
    assert transform.child_frame_id == "base_link"
    assert transform.header.stamp == source.header.stamp
    assert transform.transform.translation.x == pytest.approx(1.5)
    assert transform.transform.translation.y == pytest.approx(-0.25)
    assert transform.transform.translation.z == pytest.approx(0.18)
    assert transform.transform.rotation.z == pytest.approx(0.1)
    assert transform.transform.rotation.w == pytest.approx(0.9949874371)
