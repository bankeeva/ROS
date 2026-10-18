import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

URDF_XACRO = Path(__file__).resolve().parents[1] / "urdf" / "vehicle.urdf.xacro"


@pytest.fixture(scope="module")
def urdf_root():
    out = subprocess.check_output(["xacro", str(URDF_XACRO)], text=True)
    return ET.fromstring(out)


def _joints(urdf_root):
    return {j.get("name"): j for j in urdf_root.findall("joint")}


def _parent_of(urdf_root, joint_name):
    return _joints(urdf_root)[joint_name].find("parent").get("link")


def test_lidar_parent_is_base_link(urdf_root):
    assert "lidar_joint" in _joints(urdf_root)
    assert _parent_of(urdf_root, "lidar_joint") == "base_link"


def test_camera_parent_is_base_link(urdf_root):
    assert _parent_of(urdf_root, "camera_joint") == "base_link"


def test_imu_parent_is_base_link(urdf_root):
    assert _parent_of(urdf_root, "imu_joint") == "base_link"


def test_all_links_have_inertial(urdf_root):
    for link in urdf_root.findall("link"):
        name = link.get("name")
        assert link.find("inertial") is not None, f"{name} has no <inertial>"


def test_tree_has_no_cycles(urdf_root):
    parents = {
        j.find("child").get("link"): j.find("parent").get("link")
        for j in urdf_root.findall("joint")
    }
    for start in parents:
        seen = {start}
        cur = parents[start]
        while cur in parents:
            assert cur not in seen, f"cycle detected at {cur}"
            seen.add(cur)
            cur = parents[cur]
