from unittest.mock import patch

import pytest

import src.services.soundboard.service as svc


def test_get_sounds_delegates_to_repository():
    rows = [{"name": "a", "file_name": "a.mp3", "volume": 1.0}]
    with patch.object(svc.DatabaseOperations, "get_all_sounds", return_value=rows) as g:
        assert svc.get_sounds() == rows
    g.assert_called_once()


@pytest.mark.asyncio
async def test_upload_sound_file_normalizes_then_stores():
    with (
        patch.object(svc, "normalize_audio", return_value=b"normalized") as norm,
        patch.object(svc.storage, "put_bytes") as put,
        patch.object(svc.DatabaseOperations, "add_sound") as add,
        patch.object(svc.SoundCache, "invalidate") as invalidate,
    ):
        await svc.upload_sound_file("My Sound", b"raw-audio", "boom.mp3", "audio/mpeg")

    norm.assert_called_once_with(b"raw-audio", ".mp3")
    put.assert_called_once_with("soundboard/boom.mp3", b"normalized", "audio/mpeg")
    add.assert_called_once_with("My Sound", "boom.mp3")
    invalidate.assert_called_once()


@pytest.mark.asyncio
async def test_upload_sound_file_defaults_content_type():
    with (
        patch.object(svc, "normalize_audio", return_value=b"n"),
        patch.object(svc.storage, "put_bytes") as put,
        patch.object(svc.DatabaseOperations, "add_sound"),
        patch.object(svc.SoundCache, "invalidate"),
    ):
        await svc.upload_sound_file("n", b"x", "f.wav", None)

    assert put.call_args.args[2] == "application/octet-stream"


@pytest.mark.asyncio
async def test_upload_sound_file_wraps_errors():
    with (
        patch.object(svc, "normalize_audio", return_value=b"n"),
        patch.object(svc.storage, "put_bytes", side_effect=RuntimeError("boom")),
        patch.object(svc.DatabaseOperations, "add_sound"),
        patch.object(svc.SoundCache, "invalidate"),
    ):
        with pytest.raises(ValueError, match="Could not upload sound file"):
            await svc.upload_sound_file("n", b"x", "f.mp3", "audio/mpeg")


def test_rename_sound_updates_and_invalidates():
    with (
        patch.object(svc.DatabaseOperations, "rename_sound") as rename,
        patch.object(svc.SoundCache, "invalidate") as invalidate,
    ):
        svc.rename_sound("Old", "New")

    rename.assert_called_once_with("Old", "New")
    invalidate.assert_called_once()


@pytest.mark.asyncio
async def test_delete_sound_removes_from_all_stores():
    with (
        patch.object(svc.storage, "remove") as remove,
        patch.object(svc.DatabaseOperations, "delete_sound") as db_delete,
        patch.object(svc.FileOperations, "delete_local_file") as local_delete,
        patch.object(svc.SoundCache, "invalidate") as invalidate,
    ):
        await svc.delete_sound("My Sound", "boom.mp3")

    remove.assert_called_once_with("soundboard/boom.mp3")
    db_delete.assert_called_once_with("My Sound")
    local_delete.assert_called_once_with("boom.mp3")
    invalidate.assert_called_once()


def test_download_sound_file_fetches_to_cache():
    with (
        patch.object(svc.SoundCache, "ensure_cache_dir") as ensure,
        patch.object(svc.storage, "fget") as fget,
    ):
        svc.download_sound_file("boom.mp3")

    ensure.assert_called_once()
    assert fget.call_args.args[0] == "soundboard/boom.mp3"
