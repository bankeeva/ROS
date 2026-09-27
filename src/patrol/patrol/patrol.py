import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from turtlesim_msgs.msg import Pose

from patrol.command import choose_command


class Patrol(Node):
    def __init__(self):
        super().__init__('patrol')
        self.latest_pose = None

        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self._on_pose, 10)

        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)

        self.timer = self.create_timer(0.1, self._on_timer)

    def _on_pose(self, msg):
        self.latest_pose = msg

    def _on_timer(self):
        cmd = choose_command(self.latest_pose)
        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = Patrol()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()