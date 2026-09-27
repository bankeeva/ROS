from geometry_msgs.msg import Twist
from patrol.command import choose_command


class FakePose:
    pass


def test_no_pose_gives_zero_command():
    cmd = choose_command(None)
    assert isinstance(cmd, Twist)
    assert cmd.linear.x == 0.0
    assert cmd.angular.z == 0.0


def test_with_pose_gives_nonzero_command():
    cmd = choose_command(FakePose())
    assert cmd.linear.x == 0.5
    assert cmd.angular.z == 0.3


def test_command_sign_and_units_preserved():
    cmd = choose_command(FakePose())
    assert cmd.linear.x > 0
    assert cmd.angular.z > 0