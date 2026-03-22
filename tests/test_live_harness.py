
import importlib.util
import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec('robyn') is None, reason='robyn not installed in this environment')


def test_live_harness_placeholder_import():
    import robyn  # noqa: F401
    assert robyn is not None
