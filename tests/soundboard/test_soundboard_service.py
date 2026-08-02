from unittest.mock import patch

import pytest

import src.services.soundboard.service as svc


def test_get_sounds_delegates_to_repository_with_guild():
    rows = [{"name": "a", "file_name": "a.mp3", "volume": 1.0}]
    with patch.object(svc.DatabaseOperations, "get_all_sounds", return_value=rows) as g:
        assert svc.get_sounds(999) == rows
    g.assert_called_once_with(999)


@pytest.mark.asyncio
async def test_upload_sound_file_normalizes_then_stores():
    with (
        patch.object(svc, "normalize_audio", return_value=b"normalized") as norm,
        patch.object(svc.storage, "put_bytes") as put,
        patch.object(svc.DatabaseOperations, "add_sound") as add,
    ):
        await svc.upload_sound_file(999, "My Sound", b"raw-audio", "boom.mp3", "audio/mpeg")

    norm.assert_called_once_with(b"raw-audio", ".mp3")
    put.assert_called_once_with("soundboard/999_boom.mp3", b"normalized", "audio/mpeg")
    add.assert_called_once_with(999, "My Sound", "999_boom.mp3")


@pytest.mark.asyncio
async def test_upload_sound_file_namespaces_the_file_per_guild():
    # Two guilds uploading the same file name must not share one stored object.
    with (
        patch.object(svc, "normalize_audio", return_value=b"n"),
        patch.object(svc.storage, "put_bytes") as put,
        patch.object(svc.DatabaseOperations, "add_sound"),
    ):
        await svc.upload_sound_file(1, "Boom", b"x", "boom.mp3", "audio/mpeg")
        await svc.upload_sound_file(2, "Boom", b"x", "boom.mp3", "audio/mpeg")

    keys = [call.args[0] for call in put.call_args_list]
    assert keys == ["soundboard/1_boom.mp3", "soundboard/2_boom.mp3"]


@pytest.mark.asyncio
async def test_upload_sound_file_defaults_content_type():
    with (
        patch.object(svc, "normalize_audio", return_value=b"n"),
        patch.object(svc.storage, "put_bytes") as put,
        patch.object(svc.DatabaseOperations, "add_sound"),
    ):
        await svc.upload_sound_file(999, "n", b"x", "f.wav", None)

    assert put.call_args.args[2] == "application/octet-stream"


@pytest.mark.asyncio
async def test_upload_sound_file_wraps_errors():
    with (
        patch.object(svc, "normalize_audio", return_value=b"n"),
        patch.object(svc.storage, "put_bytes", side_effect=RuntimeError("boom")),
        patch.object(svc.DatabaseOperations, "add_sound"),
    ):
        with pytest.raises(ValueError, match="Could not upload sound file"):
            await svc.upload_sound_file(999, "n", b"x", "f.mp3", "audio/mpeg")


def test_rename_sound_updates_the_row():
    with patch.object(svc.DatabaseOperations, "rename_sound") as rename:
        svc.rename_sound(999, "Old", "New")

    rename.assert_called_once_with(999, "Old", "New")


def test_set_volume_is_scoped_to_the_guild():
    with patch.object(svc.DatabaseOperations, "set_volume") as set_volume:
        svc.set_volume(999, "My Sound", 0.5)

    set_volume.assert_called_once_with(999, "My Sound", 0.5)


@pytest.mark.asyncio
async def test_delete_sound_removes_from_all_stores():
    with (
        patch.object(svc.storage, "remove") as remove,
        patch.object(svc.DatabaseOperations, "delete_sound") as db_delete,
        patch.object(svc.FileOperations, "delete_local_file") as local_delete,
    ):
        await svc.delete_sound(999, "My Sound", "999_boom.mp3")

    remove.assert_called_once_with("soundboard/999_boom.mp3")
    db_delete.assert_called_once_with(999, "My Sound")
    local_delete.assert_called_once_with("999_boom.mp3")


def test_download_sound_file_fetches_to_cache():
    with (
        patch.object(svc.FileOperations, "ensure_cache_dir") as ensure,
        patch.object(svc.storage, "fget") as fget,
    ):
        svc.download_sound_file("boom.mp3")

    ensure.assert_called_once()
    assert fget.call_args.args[0] == "soundboard/boom.mp3"
