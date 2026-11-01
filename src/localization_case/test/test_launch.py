import importlib.util
from pathlib import Path

from launch.actions import DeclareLaunchArgument

LAUNCH_PATH = Path(__file__).resolve().parents[1] / "launch" / "localization.launch.py"


def _load_launch_module():
    spec = importlib.util.spec_from_file_location("localization_launch", LAUNCH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_nodes_contract() -> None:
    module = _load_launch_module()
    nodes = module.build_nodes("/tmp/amcl.yaml", "/tmp/map.yaml")
    assert [node.node_package for node in nodes] == [
        "nav2_map_server",
        "nav2_amcl",
        "nav2_lifecycle_manager",
    ]
    assert [node.node_executable for node in nodes] == [
        "map_server",
        "amcl",
        "lifecycle_manager",
    ]


def test_launch_declares_arguments_and_node_names() -> None:
    module = _load_launch_module()
    description = module.generate_launch_description()
    declared = [
        entity.name
        for entity in description.entities
        if isinstance(entity, DeclareLaunchArgument)
    ]
    assert declared == ["params_file", "map"]
    source = LAUNCH_PATH.read_text(encoding="utf-8")
    assert 'name="map_server"' in source
    assert 'name="amcl"' in source
    assert 'name="lifecycle_manager_localization"' in source


def test_missing_map_is_rejected() -> None:
    module = _load_launch_module()
    try:
        module._resolve_file("/definitely/missing/map.yaml", "map")
    except RuntimeError as error:
        assert "map.yaml" in str(error)
    else:
        raise AssertionError("missing map was accepted")
