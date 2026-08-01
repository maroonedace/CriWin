from src.commands.soundboard import volume


def setup_function():
    volume._user_volumes.clear()


def test_resolve_uses_stored_when_unset():
    assert volume.resolve_volume(1, 0.8) == 0.8


def test_resolve_prefers_personal_when_set():
    volume.set_user_volume(1, 1.5)
    assert volume.resolve_volume(1, 0.8) == 1.5


def test_personal_volume_is_per_user():
    volume.set_user_volume(1, 2.0)
    assert volume.resolve_volume(1, 0.8) == 2.0
    assert volume.resolve_volume(2, 0.8) == 0.8  # unaffected


def test_get_user_volume():
    assert volume.get_user_volume(1) is None
    volume.set_user_volume(1, 2.0)
    assert volume.get_user_volume(1) == 2.0
