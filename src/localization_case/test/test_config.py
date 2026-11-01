from pathlib import Path

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    return yaml.safe_load((PACKAGE_ROOT / "config" / name).read_text(encoding="utf-8"))


def test_amcl_profile_contract() -> None:
    config = _load("amcl.yaml")
    amcl = config["amcl"]["ros__parameters"]
    assert amcl["use_sim_time"] is True
    assert amcl["base_frame_id"] == "base_link"
    assert amcl["odom_frame_id"] == "odom"
    assert amcl["global_frame_id"] == "map"
    assert amcl["scan_topic"] == "/vehicle/scan"
    assert amcl["map_topic"] == "/map"
    assert amcl["tf_broadcast"] is True
    assert amcl["set_initial_pose"] is True
    assert amcl["always_reset_initial_pose"] is True
    assert amcl["initial_pose"] == {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0}
    assert amcl["save_pose_rate"] == -1.0


def test_map_server_and_lifecycle_sections() -> None:
    config = _load("amcl.yaml")
    assert config["map_server"]["ros__parameters"]["use_sim_time"] is True
    manager = config["lifecycle_manager_localization"]["ros__parameters"]
    assert manager["autostart"] is True
    assert manager["node_names"] == ["map_server", "amcl"]


def test_defect_profile_differs_only_by_base_frame() -> None:
    good = _load("amcl.yaml")
    defect = _load("amcl-defect.yaml")
    assert defect["amcl"]["ros__parameters"]["base_frame_id"] == "chassis"
    good["amcl"]["ros__parameters"]["base_frame_id"] = "chassis"
    assert defect == good
