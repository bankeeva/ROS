import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def build_nodes(params_file: str, map_path: str) -> list[Node]:
    return [
        Node(
            package="nav2_map_server",
            executable="map_server",
            name="map_server",
            output="screen",
            parameters=[
                params_file,
                {"yaml_filename": map_path, "use_sim_time": True},
            ],
        ),
        Node(
            package="nav2_amcl",
            executable="amcl",
            name="amcl",
            output="screen",
            parameters=[
                params_file,
                {"use_sim_time": True},
            ],
        ),
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_localization",
            output="screen",
            parameters=[
                params_file,
                {
                    "use_sim_time": True,
                    "autostart": True,
                    "node_names": ["map_server", "amcl"],
                },
            ],
        ),
    ]


def _resolve_file(value: str, label: str) -> str:
    path = os.path.abspath(value)
    if not os.path.isfile(path):
        raise RuntimeError(f"{label} file does not exist: {path}")
    return path


def _launch_setup(context, *args, **kwargs):
    params_file = _resolve_file(
        LaunchConfiguration("params_file").perform(context), "params_file"
    )
    map_path = _resolve_file(LaunchConfiguration("map").perform(context), "map")
    return build_nodes(params_file, map_path)


def generate_launch_description() -> LaunchDescription:
    default_params = os.path.join(
        get_package_share_directory("localization_case"), "config", "amcl.yaml"
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "params_file",
                default_value=default_params,
                description="AMCL, map server and lifecycle manager parameters",
            ),
            DeclareLaunchArgument(
                "map",
                default_value="",
                description="Absolute path to the map YAML file",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
