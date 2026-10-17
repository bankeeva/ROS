import math

from geometry_msgs.msg import Twist
from rcl_interfaces.msg import SetParametersResult
import rclpy
from rclpy.node import Node
from turtlesim_msgs.msg import Pose


class PatrolNode(Node):

    def __init__(self):
        super().__init__('patrol')

        self.declare_parameter('linear_speed', 0.5)
        self.declare_parameter('turn_rate', 0.3)
        self.declare_parameter('publish_hz', 10.0)

        self.add_on_set_parameters_callback(self._on_parameter_change)

        self.linear_speed = self.get_parameter('linear_speed').value
        self.turn_rate = self.get_parameter('turn_rate').value
        self.publish_hz = self.get_parameter('publish_hz').value

        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self._pose_cb, 10)
        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        period = 1.0 / self.publish_hz
        self.timer = self.create_timer(period, self._timer_callback)

        self.get_logger().info(
            f'Patrol started: speed={self.linear_speed}, '
            f'turn={self.turn_rate}, hz={self.publish_hz}'
        )

    def _pose_cb(self, msg: Pose):
        self.current_pose = msg

    def _timer_callback(self):
        msg = Twist()
        msg.linear.x = self.linear_speed
        msg.angular.z = self.turn_rate
        self.cmd_pub.publish(msg)

    def _on_parameter_change(self, params):
        for p in params:
            if p.name == 'linear_speed':
                if not isinstance(p.value, (int, float)):
                    return SetParametersResult(
                        successful=False, reason='must be number')
                if not (0.0 <= p.value <= 1.0):
                    return SetParametersResult(
                        successful=False,
                        reason='linear_speed must be in [0, 1]')

            elif p.name == 'turn_rate':
                if not isinstance(p.value, (int, float)):
                    return SetParametersResult(
                        successful=False, reason='must be number')
                if not (-1.0 <= p.value <= 1.0):
                    return SetParametersResult(
                        successful=False,
                        reason='turn_rate must be in [-1, 1]')

            elif p.name == 'publish_hz':
                if not isinstance(p.value, (int, float)):
                    return SetParametersResult(
                        successful=False, reason='must be number')
                if math.isnan(p.value):
                    return SetParametersResult(
                        successful=False, reason='NaN is not allowed')
                if not (1.0 <= p.value <= 30.0):
                    return SetParametersResult(
                        successful=False,
                        reason='publish_hz must be in [1, 30]')

        for p in params:
            if p.name == 'linear_speed':
                self.linear_speed = float(p.value)
            elif p.name == 'turn_rate':
                self.turn_rate = float(p.value)
            elif p.name == 'publish_hz':
                new_hz = float(p.value)
                if new_hz != self.publish_hz:
                    self.timer.cancel()
                    self.publish_hz = new_hz
                    period = 1.0 / self.publish_hz
                    self.timer = self.create_timer(
                        period, self._timer_callback)
                    self.get_logger().info(
                        f'Timer recreated: period={period}s')

        return SetParametersResult(successful=True)


def main():
    rclpy.init()
    node = PatrolNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
