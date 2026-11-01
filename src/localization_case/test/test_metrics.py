import hashlib
import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "localization_metrics.py"
)


def _load_metrics_module():
    spec = importlib.util.spec_from_file_location("localization_metrics", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_window_bounds_use_recorded_clock() -> None:
    module = _load_metrics_module()
    start_ns, end_ns = module.window_bounds(93_162_000_000, 10.0, 20.0)
    assert start_ns == 103_162_000_000
    assert end_ns == 123_162_000_000


def test_covariance_sum_and_median() -> None:
    module = _load_metrics_module()
    covariance = [0.0] * 36
    covariance[0] = 0.04
    covariance[7] = 0.09
    assert module.xy_covariance_sum(covariance) == 0.13
    assert module.median_covariance([0.3, 0.1, 0.2]) == 0.2


def test_median_for_empty_sample_is_zero() -> None:
    module = _load_metrics_module()
    assert module.median_covariance([]) == 0.0


def test_sha256_file(tmp_path: Path) -> None:
    module = _load_metrics_module()
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"pr08")
    assert module.sha256_file(str(sample)) == hashlib.sha256(b"pr08").hexdigest()
