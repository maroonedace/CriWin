from pathlib import Path
from unittest.mock import MagicMock

import src.services.processing as processing


def test_normalize_builds_loudnorm_command(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        Path(cmd[-1]).write_bytes(b"normalized-bytes")
        return MagicMock(returncode=0)

    monkeypatch.setattr(processing.subprocess, "run", fake_run)

    result = processing.normalize_audio(b"raw-audio", ".mp3")

    assert result == b"normalized-bytes"
    assert captured["cmd"][0] == "ffmpeg"
    assert any("loudnorm" in str(part) for part in captured["cmd"])


def test_normalize_falls_back_on_ffmpeg_failure(monkeypatch):
    monkeypatch.setattr(processing.subprocess, "run", lambda cmd, **kw: MagicMock(returncode=1))
    assert processing.normalize_audio(b"raw-audio", ".wav") == b"raw-audio"


def test_normalize_falls_back_when_ffmpeg_missing(monkeypatch):
    def raise_missing(cmd, **kw):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(processing.subprocess, "run", raise_missing)
    assert processing.normalize_audio(b"raw-audio", ".mp3") == b"raw-audio"
