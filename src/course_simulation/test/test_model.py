import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MODEL_SDF = PACKAGE_ROOT / "models" / "course_ackermann" / "model.sdf"
MODEL_CONFIG = PACKAGE_ROOT / "models" / "course_ackermann" / "model.config"
WORLD_SDF = PACKAGE_ROOT / "worlds" / "mcity-minimal.sdf"


def _root(path: Path):
    return ET.parse(path).getroot()


def _text(element, tag, default=None):
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else default


def test_sensors_expose_contract_topics_and_frames():
    root = _root(MODEL_SDF)
    sensors = {sensor.get("name"): sensor for sensor in root.iter("sensor")}
    assert {"front_camera", "lidar", "imu"} <= set(sensors)

    camera = sensors["front_camera"]
    assert camera.get("type") == "camera"
    assert _text(camera, "topic") == "/vehicle/camera/image_raw"
    assert _text(camera, "frame_id") == "camera_link"
    assert _text(camera, "gz_frame_id") == "camera_link"
    assert float(_text(camera, "update_rate")) == 10.0

    lidar = sensors["lidar"]
    assert lidar.get("type") == "gpu_lidar"
    assert _text(lidar, "topic") == "/vehicle/scan"
    assert _text(lidar, "frame_id") == "lidar_link"
    assert _text(lidar, "gz_frame_id") == "lidar_link"
    assert float(_text(lidar, "update_rate")) == 10.0

    imu = sensors["imu"]
    assert imu.get("type") == "imu"
    assert _text(imu, "topic") == "/vehicle/imu"
    assert _text(imu, "frame_id") == "imu_link"
    assert _text(imu, "gz_frame_id") == "imu_link"
    assert float(_text(imu, "update_rate")) == 100.0


def test_ackermann_plugin_matches_contract():
    root = _root(MODEL_SDF)
    plugin = root.find(".//plugin[@filename='gz-sim-ackermann-steering-system']")
    assert plugin is not None
    assert _text(plugin, "wheel_base") == "0.8"
    assert _text(plugin, "steering_limit") == "0.45"
    assert _text(plugin, "topic") == "/model/course_ackermann/cmd_vel"
    assert _text(plugin, "odom_publish_frequency") == "50"
    assert _text(plugin, "min_acceleration") is not None


def test_wheel_joints_roll_about_the_lateral_axis():
    root = _root(MODEL_SDF)
    wheel_joints = [
        joint for joint in root.iter("joint") if joint.get("name", "").endswith("_wheel_joint")
    ]
    assert len(wheel_joints) == 4
    for joint in wheel_joints:
        axis = joint.find("axis/xyz")
        assert axis is not None
        assert axis.text.strip() == "0 1 0"
        assert axis.get("expressed_in") == "__model__"


def test_model_config_points_to_the_sdf():
    root = _root(MODEL_CONFIG)
    assert _text(root, "sdf") == "model.sdf"
    assert _text(root, "name")


def test_world_includes_exactly_one_robot():
    root = _root(WORLD_SDF)
    world = root.find("world")
    assert world is not None
    includes = [include for include in world.iter("include")]
    uris = [_text(include, "uri") for include in includes]
    assert uris == ["model://course_ackermann"]
    assert world.get("name") == "mcity_minimal"


def test_world_has_required_systems():
    root = _root(WORLD_SDF)
    world = root.find("world")
    plugins = {plugin.get("filename") for plugin in world.iter("plugin")}
    for required in (
        "gz-sim-physics-system",
        "gz-sim-user-commands-system",
        "gz-sim-scene-broadcaster-system",
        "gz-sim-sensors-system",
        "gz-sim-imu-system",
    ):
        assert required in plugins
    sensors = world.find(".//plugin[@filename='gz-sim-sensors-system']")
    assert _text(sensors, "render_engine") == "ogre2"
    physics = world.find("physics")
    assert _text(physics, "max_step_size") == "0.001"
    assert _text(physics, "real_time_factor") == "1.0"
