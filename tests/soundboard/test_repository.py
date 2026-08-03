"""Covers the soundboard repository against a real Postgres database.

Every test here runs the statements SQLAlchemy actually builds, so it catches the
things a mocked Session cannot: server defaults firing, ON CONFLICT resolving,
Postgres arrays round-tripping, and the dict shapes the admin panel subscripts.
"""

import pytest
from sqlalchemy import text

import src.services.db as db
import src.services.soundboard.repository as repo
from src.config import Config

Operations = repo.DatabaseOperations

pytestmark = pytest.mark.usefixtures("db")


def _seed(db_engine, statement: str, **params) -> None:
    with db_engine.begin() as connection:
        connection.execute(text(statement), params)


class TestDatabaseUrl:
    def test_escapes_special_characters_in_password(self, monkeypatch):
        """A password with URL metacharacters must survive intact.

        Concatenating the URL by hand breaks here: '@' would end the userinfo
        section early and point the driver at the wrong host.
        """
        monkeypatch.setattr(Config, "DB_USER", "criwin")
        monkeypatch.setattr(Config, "DB_PASSWORD", "p@ss/w%rd")
        monkeypatch.setattr(Config, "DB_HOST", "db")
        monkeypatch.setattr(Config, "DB_PORT", 5432)
        monkeypatch.setattr(Config, "DB_NAME", "criwin")

        url = db.database_url()

        assert url.password == "p@ss/w%rd"
        assert url.host == "db"
        assert url.database == "criwin"
        assert "p@ss/w%rd" not in url.render_as_string(hide_password=False).split("@")[-1]


class TestSounds:
    def test_get_all_sounds_returns_the_shape_callers_subscript(self, db):
        _seed(
            db,
            "INSERT INTO sounds (guild_id, name, file_name, volume) "
            "VALUES (999, 'Boom', '999_boom.mp3', 0.5)",
        )

        result = Operations.get_all_sounds(999)

        assert result == [{"name": "Boom", "file_name": "999_boom.mp3", "volume": 0.5}]
        assert isinstance(result[0]["volume"], float)

    def test_get_all_sounds_is_scoped_to_one_guild(self, db):
        _seed(db, "INSERT INTO sounds (guild_id, name, file_name) VALUES (999, 'Mine', 'a.mp3')")
        _seed(db, "INSERT INTO sounds (guild_id, name, file_name) VALUES (111, 'Theirs', 'b.mp3')")

        assert [sound["name"] for sound in Operations.get_all_sounds(999)] == ["Mine"]

    def test_get_all_sounds_orders_by_name(self, db):
        _seed(db, "INSERT INTO sounds (guild_id, name, file_name) VALUES (999, 'Zebra', 'z.mp3')")
        _seed(db, "INSERT INTO sounds (guild_id, name, file_name) VALUES (999, 'Apple', 'a.mp3')")

        assert [sound["name"] for sound in Operations.get_all_sounds(999)] == ["Apple", "Zebra"]

    def test_get_all_sounds_is_empty_for_an_unknown_guild(self, db):
        assert Operations.get_all_sounds(999) == []

    def test_add_sound_records_the_guild(self, db):
        Operations.add_sound(999, "My Sound", "999_boom.mp3")

        assert Operations.get_all_sounds(999) == [
            {"name": "My Sound", "file_name": "999_boom.mp3", "volume": 1.0}
        ]

    def test_add_sound_fills_in_the_server_defaults(self, db):
        """add_sound omits volume and created_at, so the columns' defaults must fire.

        Dropping either server_default from the model would only break a freshly
        created database -- every existing one already carries the default -- so this
        is the guard against that going unnoticed.
        """
        Operations.add_sound(999, "My Sound", "999_boom.mp3")

        with db.begin() as connection:
            volume, created_at = connection.execute(
                text("SELECT volume, created_at FROM sounds WHERE name = 'My Sound'")
            ).one()

        assert volume == 1.0
        assert created_at is not None

    def test_add_sound_rejects_a_duplicate_name_within_a_guild(self, db):
        Operations.add_sound(999, "My Sound", "a.mp3")

        with pytest.raises(ValueError):
            Operations.add_sound(999, "My Sound", "b.mp3")

    def test_add_sound_allows_the_same_name_in_another_guild(self, db):
        Operations.add_sound(999, "My Sound", "999_a.mp3")
        Operations.add_sound(111, "My Sound", "111_a.mp3")

        assert len(Operations.get_all_sounds(999)) == 1
        assert len(Operations.get_all_sounds(111)) == 1

    def test_delete_sound_is_scoped_to_the_guild(self, db):
        Operations.add_sound(999, "My Sound", "999_a.mp3")
        Operations.add_sound(111, "My Sound", "111_a.mp3")

        Operations.delete_sound(999, "My Sound")

        assert Operations.get_all_sounds(999) == []
        assert len(Operations.get_all_sounds(111)) == 1

    def test_set_volume_updates_the_row(self, db):
        Operations.add_sound(999, "My Sound", "a.mp3")

        Operations.set_volume(999, "My Sound", 0.5)

        assert Operations.get_all_sounds(999)[0]["volume"] == 0.5

    def test_set_volume_is_scoped_to_the_guild(self, db):
        Operations.add_sound(999, "My Sound", "999_a.mp3")
        Operations.add_sound(111, "My Sound", "111_a.mp3")

        Operations.set_volume(999, "My Sound", 0.5)

        assert Operations.get_all_sounds(111)[0]["volume"] == 1.0

    def test_rename_updates_the_display_name_only(self, db):
        Operations.add_sound(999, "Old", "999_a.mp3")

        Operations.rename_sound(999, "Old", "New")

        assert Operations.get_all_sounds(999) == [
            {"name": "New", "file_name": "999_a.mp3", "volume": 1.0}
        ]


class TestPanels:
    def test_get_panel_returns_the_row_for_the_guild(self, db):
        Operations.save_panel(777, 999, [1, 2])

        assert Operations.get_panel(777) == {"channel_id": 999, "message_ids": [1, 2]}

    def test_get_panel_returns_none_when_absent(self, db):
        assert Operations.get_panel(777) is None

    def test_save_panel_upserts_rather_than_duplicating(self, db):
        Operations.save_panel(777, 999, [1, 2])
        Operations.save_panel(777, 888, [3])

        assert Operations.get_panel(777) == {"channel_id": 888, "message_ids": [3]}
        assert len(Operations.get_all_panels()) == 1

    def test_save_panel_round_trips_discord_sized_message_ids(self, db):
        """Snowflake ids exceed 32 bits, so the array has to be BIGINT[]."""
        message_ids = [1234567890123456789, 1420070400000000000]

        Operations.save_panel(777, 999, message_ids)

        assert Operations.get_panel(777)["message_ids"] == message_ids

    def test_save_panel_accepts_an_empty_message_list(self, db):
        Operations.save_panel(777, 999, [])

        assert Operations.get_panel(777)["message_ids"] == []

    def test_get_all_panels_returns_every_guild(self, db):
        Operations.save_panel(777, 999, [1])
        Operations.save_panel(888, 111, [])

        result = Operations.get_all_panels()

        assert sorted(row["guild_id"] for row in result) == [777, 888]
        assert set(result[0]) == {"guild_id", "channel_id", "message_ids"}


class TestGuilds:
    def test_get_guilds_orders_by_name(self, db):
        Operations.upsert_guild(2, "Beta")
        Operations.upsert_guild(1, "Alpha")

        assert Operations.get_guilds() == [
            {"guild_id": 1, "name": "Alpha"},
            {"guild_id": 2, "name": "Beta"},
        ]

    def test_upsert_guild_refreshes_the_name(self, db):
        Operations.upsert_guild(999, "Old Name")
        Operations.upsert_guild(999, "New Name")

        assert Operations.get_guilds() == [{"guild_id": 999, "name": "New Name"}]

    def test_upsert_guild_bumps_updated_at(self, db):
        Operations.upsert_guild(999, "My Server")
        with db.begin() as connection:
            first = connection.execute(text("SELECT updated_at FROM guilds")).scalar_one()

        Operations.upsert_guild(999, "My Server")
        with db.begin() as connection:
            second = connection.execute(text("SELECT updated_at FROM guilds")).scalar_one()

        assert second >= first


class TestAccessRoles:
    def test_get_access_role_ids_is_empty_by_default(self, db):
        assert Operations.get_access_role_ids(999) == []

    def test_add_and_get_access_roles(self, db):
        Operations.add_access_role(999, 11)
        Operations.add_access_role(999, 22)

        assert sorted(Operations.get_access_role_ids(999)) == [11, 22]

    def test_add_access_role_is_idempotent(self, db):
        Operations.add_access_role(999, 11)
        Operations.add_access_role(999, 11)

        assert Operations.get_access_role_ids(999) == [11]

    def test_access_roles_are_scoped_to_the_guild(self, db):
        Operations.add_access_role(999, 11)
        Operations.add_access_role(111, 22)

        assert Operations.get_access_role_ids(999) == [11]

    def test_remove_access_role_deletes_only_that_pair(self, db):
        Operations.add_access_role(999, 11)
        Operations.add_access_role(999, 22)

        Operations.remove_access_role(999, 11)

        assert Operations.get_access_role_ids(999) == [22]
