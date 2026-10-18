from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    OpaqueFunction,
    LogInfo,
    GroupAction,
)
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    namespace = LaunchConfiguration("namespace").perform(context).lstrip("/")
    record = LaunchConfiguration("record").perform(context)
    bag_dir = LaunchConfiguration("bag_dir").perform(context)
    sub_reliability = LaunchConfiguration("subscriber_reliability").perform(context)

    actions = [
        Node(
            package="turtlesim",
            executable="turtlesim_node",
            name="turtlesim",
            output="screen",
        ),
        Node(
            package="course_bringup",
            executable="pose_relay.py",
            name="pose_relay",
            namespace=namespace,
            output="screen",
            remappings=[("turtle1/pose", "/turtle1/pose")],
        ),
        LogInfo(
            msg=f"[patrol] ns=/{namespace} record={record} "
            f"bag_dir={bag_dir} sub_reliability={sub_reliability}"
        ),
    ]

    recorder = ExecuteProcess(
        cmd=[
            "ros2",
            "bag",
            "record",
            "-s",
            "mcap",
            "-o",
            bag_dir,
            f"/{namespace}/sensor_pose",
        ],
        output="screen",
    )
    actions.append(GroupAction(actions=[recorder], condition=IfCondition(record)))
    return actions


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("namespace", default_value="robot_a"),
            DeclareLaunchArgument("record", default_value="false"),
            DeclareLaunchArgument("bag_dir", default_value="evidence/pr05/bag"),
            DeclareLaunchArgument("subscriber_reliability", default_value="reliable"),
            OpaqueFunction(function=launch_setup),
        ]
    )
