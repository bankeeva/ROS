import math


def validate_hz(value):
    if not isinstance(value, (int, float)):
        return False
    if math.isnan(value):
        return False
    if not (1.0 <= value <= 30.0):
        return False
    return True


def validate_speed(value):
    if not isinstance(value, (int, float)):
        return False
    if math.isnan(value):
        return False
    if not (0.0 <= value <= 1.0):
        return False
    return True


def validate_turn(value):
    if not isinstance(value, (int, float)):
        return False
    if math.isnan(value):
        return False
    if not (-1.0 <= value <= 1.0):
        return False
    return True


def test_hz_normal_change():
    assert validate_hz(5.0) is True


def test_hz_zero_rejected():
    assert validate_hz(0.0) is False


def test_hz_negative_rejected():
    assert validate_hz(-5.0) is False


def test_hz_nan_rejected():
    assert validate_hz(float('nan')) is False


def test_hz_upper_bound():
    assert validate_hz(30.0) is True
    assert validate_hz(31.0) is False


def test_speed_normal():
    assert validate_speed(0.5) is True


def test_speed_zero():
    assert validate_speed(0.0) is True


def test_speed_over_one():
    assert validate_speed(1.5) is False


def test_turn_normal():
    assert validate_turn(0.3) is True


def test_turn_negative():
    assert validate_turn(-0.5) is True


def test_turn_over_one():
    assert validate_turn(1.5) is False
