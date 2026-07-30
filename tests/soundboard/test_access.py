from unittest.mock import MagicMock

from src.commands.soundboard.access import has_panel_access


def _member(*role_ids):
    member = MagicMock()
    member.roles = [MagicMock(id=rid) for rid in role_ids]
    return member


def test_open_when_no_roles_configured():
    assert has_panel_access(_member(1, 2), set()) is True


def test_allowed_when_member_has_a_configured_role():
    assert has_panel_access(_member(5, 9), {9, 10}) is True


def test_denied_when_member_lacks_configured_roles():
    assert has_panel_access(_member(1, 2), {9, 10}) is False
