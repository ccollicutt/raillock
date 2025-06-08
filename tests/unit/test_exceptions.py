import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)
from raillock.exceptions import RailLockError


def test_raillock_error_inheritance():
    err = RailLockError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"
