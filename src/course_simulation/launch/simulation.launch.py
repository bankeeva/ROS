import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

TRUTHY = {"1", "true", "yes", "on"}


def _flag(context, name: str) -> bool:
    return LaunchConfiguration(name).perform(context).strip().lower() in TRUTHY


def _launch_setup(context, *args, **kwargs):
    simulation_share = get_package_share_directory("course_simulation")
    description_share = get_package_share_directory("course_description")

    world = LaunchConfiguration("world").perform(context)
    bridge_config = LaunchConfiguration("bridge_config").perform(context)
    namespace = LaunchConfiguration("node_namespace").perform(context).strip()
    use_sim_time = _flag(context, "use_sim_time")
    headless = _flag(context, "headless")
    headless_rendering = _flag(context, "headless_rendering")
    use_test_source = _flag(context, "use_test_source")
    test_mode = LaunchConfiguration("test_mode").perform(context)
    test_speed = LaunchConfiguration("test_speed").perform(context)
    test_steering = LaunchConfiguration("test_steering").perform(context)

    models_dir = os.path.join(simulation_share, "models")
    existing_resource_path = os.environ.get("GZ_SIM_RESOURCE_PATH", "")
    resource_path = models_dir
    if existing_resource_path:
        resource_path = resource_path + os.pathsep + existing_resource_path

    # A single -s disables the GUI client but not the rendering sensors, so the
    # camera and gpu_lidar additionally need --headless-rendering (OGRE2/EGL).
    gz_command = ["gz", "sim"]
    if headless:
        gz_command.append("-s")
    gz_command.append("-r")
    if headless and headless_rendering:
        gz_command.append("--headless-rendering")
    gz_command.append(world)

    xacro_file = os.path.join(description_share, "urdf", "vehicle.urdf.xacro")
    robot_description = ParameterValue(
        Command(["xacro ", xacro_file]),
        value_type=str,
    )

    actions = [
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", resource_path),
        LogInfo(msg="PR07 gz server command: " + " ".join(gz_command)),
        LogInfo(msg="PR07 bridge config: " + bridge_config),
        LogInfo(msg="PR07 namespace: " + (namespace or "<root>")),
        ExecuteProcess(
            cmd=gz_command,
            name="gz_sim_server",
            output="screen",
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            namespace=namespace,
            output="screen",
            parameters=[
                {
                    "robot_description": robot_description,
                    "use_sim_time": use_sim_time,
                }
            ],
        ),
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            namespace=namespace,
            output="screen",
            parameters=[{"config_file": bridge_config}],
        ),
        Node(
            package="course_simulation",
            executable="ackermann_adapter.py",
            namespace=namespace,
            output="screen",
            parameters=[
                {
                    "use_sim_time": use_sim_time,
                    "input_topic": "/drive/safe",
                    "output_topic": "/vehicle/gz_cmd_vel",
                }
            ],
        ),
        Node(
            package="course_simulation",
            executable="odom_adapter.py",
            namespace=namespace,
            output="screen",
            parameters=[
                {
                    "use_sim_time": use_sim_time,
                    "input_topic": "/vehicle/odom_gz",
                    "output_topic": "/vehicle/odom",
                    "source_prefix": "course_ackermann",
                }
            ],
        ),
    ]

    if use_test_source:
        actions.append(
            Node(
                package="course_simulation",
                executable="test_drive_source.py",
                namespace=namespace,
                output="screen",
                parameters=[
                    {
                        "use_sim_time": use_sim_time,
                        "topic": "/drive/safe",
                        "mode": test_mode,
                        "speed": float(test_speed),
                        "steering": float(test_steering),
                    }
                ],
            )
        )
    return actions


def generate_launch_description() -> LaunchDescription:
    simulation_share = get_package_share_directory("course_simulation")
    default_world = os.path.join(simulation_share, "worlds", "mcity-minimal.sdf")
    default_bridge = os.path.join(simulation_share, "config", "bridge.yaml")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value=default_world,
                description="SDF world with the included course_ackermann model",
            ),
            DeclareLaunchArgument(
                "bridge_config",
                default_value=default_bridge,
                description="ros_gz_bridge YAML (one bridge process, six topics)",
            ),
            DeclareLaunchArgument(
                "headless",
                default_value="true",
                description="Start Gazebo without a GUI client (-s)",
            ),
            DeclareLaunchArgument(
                "headless_rendering",
                default_value="true",
                description="Pass --headless-rendering (OGRE2/EGL) for the sensors",
            ),
            DeclareLaunchArgument(
                "node_namespace",
                default_value="",
                description="Namespace for ROS nodes; contract topics stay absolute. "
                "Not named ros_namespace: that launch argument is reserved and would "
                "be applied twice.",
            ),
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="true",
                description="Use the simulation clock published on /clock",
            ),
            DeclareLaunchArgument(
                "use_test_source",
                default_value="true",
                description="Run the PR07 stand-in command source on /drive/safe",
            ),
            DeclareLaunchArgument(
                "test_mode",
                default_value="pattern",
                description="Test source mode: pattern (8 s cycle) or fixed",
            ),
            DeclareLaunchArgument(
                "test_speed",
                default_value="0.30",
                description="Speed used when test_mode:=fixed (m/s)",
            ),
            DeclareLaunchArgument(
                "test_steering",
                default_value="0.0",
                description="Steering used when test_mode:=fixed (rad)",
            ),
            OpaqueFunction(function=_launch_setup),
        ]
    )
