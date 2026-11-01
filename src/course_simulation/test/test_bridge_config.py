from pathlib import Path

import pytest
import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
BRIDGE = CONFIG_DIR / "bridge.yaml"
BROKEN = CONFIG_DIR / "bridge-broken.yaml"

SENSOR_TOPICS = ("/vehicle/camera/image_raw", "/vehicle/scan", "/vehicle/imu")

EXPECTED = {
    "/vehicle/gz_cmd_vel": {
        "gz_topic_name": "/model/course_ackermann/cmd_vel",
        "ros_type_name": "geometry_msgs/msg/Twist",
        "gz_type_name": "gz.msgs.Twist",
        "direction": "ROS_TO_GZ",
    },
    "/vehicle/odom_gz": {
        "gz_topic_name": "/model/course_ackermann/odometry",
        "ros_type_name": "nav_msgs/msg/Odometry",
        "gz_type_name": "gz.msgs.Odometry",
        "direction": "GZ_TO_ROS",
    },
    "/vehicle/scan": {
        "gz_topic_name": "/vehicle/scan",
        "ros_type_name": "sensor_msgs/msg/LaserScan",
        "gz_type_name": "gz.msgs.LaserScan",
        "direction": "GZ_TO_ROS",
    },
    "/vehicle/imu": {
        "gz_topic_name": "/vehicle/imu",
        "ros_type_name": "sensor_msgs/msg/Imu",
        "gz_type_name": "gz.msgs.IMU",
        "direction": "GZ_TO_ROS",
    },
    "/vehicle/camera/image_raw": {
        "gz_topic_name": "/vehicle/camera/image_raw",
        "ros_type_name": "sensor_msgs/msg/Image",
        "gz_type_name": "gz.msgs.Image",
        "direction": "GZ_TO_ROS",
    },
    "/clock": {
        "gz_topic_name": "/clock",
        "ros_type_name": "rosgraph_msgs/msg/Clock",
        "gz_type_name": "gz.msgs.Clock",
        "direction": "GZ_TO_ROS",
    },
}


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def collect_errors(entries) -> list[str]:
    errors: list[str] = []
    if not isinstance(entries, list):
        return ["bridge config must be a YAML list"]

    by_ros = {}
    for entry in entries:
        if not isinstance(entry, dict) or "ros_topic_name" not in entry:
            errors.append(f"malformed bridge entry: {entry!r}")
            continue
        by_ros[entry["ros_topic_name"]] = entry

    for ros_topic, expected in EXPECTED.items():
        entry = by_ros.get(ros_topic)
        if entry is None:
            errors.append(f"missing bridge for {ros_topic}")
            continue
        for key, value in expected.items():
            if entry.get(key) != value:
                errors.append(
                    f"{ros_topic}: {key}={entry.get(key)!r}, expected {value!r}"
                )

    if len(by_ros) != len(entries):
        errors.append("duplicate ros_topic_name entries")
    if len(entries) != len(EXPECTED):
        errors.append(
            f"expected {len(EXPECTED)} bridges in one config, got {len(entries)}"
        )

    for forbidden in ("/drive/raw", "/drive/safe"):
        if forbidden in by_ros:
            errors.append(f"{forbidden} must not be bridged directly to Gazebo")

    for entry in entries:
        ros_topic = entry.get("ros_topic_name")
        qos = entry.get("qos_profile")
        if ros_topic in SENSOR_TOPICS and qos != "SENSOR_DATA":
            errors.append(f"{ros_topic}: sensor topic must use SENSOR_DATA QoS")
        if ros_topic in ("/vehicle/gz_cmd_vel", "/vehicle/odom_gz"):
            if qos == "SENSOR_DATA":
                errors.append(f"{ros_topic}: reliable topic must not use SENSOR_DATA")
        if ros_topic == "/clock" and qos != "CLOCK":
            errors.append("/clock must use the CLOCK QoS profile")
    return errors


def test_bridge_config_matches_contract():
    errors = collect_errors(load(BRIDGE))
    assert errors == []


def test_config_has_no_bypass_around_safe_topic():
    ros_topics = {entry["ros_topic_name"] for entry in load(BRIDGE)}
    assert "/drive/raw" not in ros_topics
    assert "/drive/safe" not in ros_topics


def test_defect_copy_is_detected():
    errors = collect_errors(load(BROKEN))
    assert errors, "the defect copy must fail the same validation as the fixed one"
    assert any("/vehicle/imu" in error for error in errors)


def test_broken_and_good_configs_differ_only_in_imu():
    good = {entry["ros_topic_name"]: entry for entry in load(BRIDGE)}
    broken = {entry["ros_topic_name"]: entry for entry in load(BROKEN)}
    different = {
        topic for topic in good if good[topic] != broken.get(topic)
    }
    assert different == {"/vehicle/imu"}


@pytest.mark.parametrize("topic", SENSOR_TOPICS)
def test_sensor_qos_profile(topic):
    entries = {entry["ros_topic_name"]: entry for entry in load(BRIDGE)}
    assert entries[topic]["qos_profile"] == "SENSOR_DATA"
