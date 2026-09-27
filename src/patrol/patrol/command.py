from geometry_msgs.msg import Twist


def choose_command(pose) -> Twist:
    cmd = Twist()
    if pose is None:
        return cmd
    cmd.linear.x = 0.5
    cmd.angular.z = 0.3
    return cmd