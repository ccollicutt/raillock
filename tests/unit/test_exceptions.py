from raillock.exceptions import RailLockError


def test_raillock_error_inheritance():
    err = RailLockError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"
