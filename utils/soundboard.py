import re
import json
import threading
from pathlib import Path
from typing import Dict, Tuple, List

import discord

SOUNDS_JSON = Path("./sounds/sounds.json")
_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

_lock = threading.Lock()
_cache: Dict[str, str] = {}
_cache_mtime: float = -1.0
_base_dir = Path("./sounds")

def load_sounds() -> Tuple[Dict[str, List], Path]:
    global _cache, _cache_mtime, _base_dir
    try:
        mtime = SOUNDS_JSON.stat().st_mtime
    except FileNotFoundError:
        _cache, _cache_mtime = {}, -1.0
        _base_dir = Path("./sounds")
        return _cache, _base_dir

    if mtime != _cache_mtime:
        data = json.loads(SOUNDS_JSON.read_text(encoding="utf-8"))
        _cache = data
        _cache_mtime = mtime
        _base_dir = Path(_cache.get("base_dir", "./sounds"))
    return _cache, _base_dir

def save_index_atomic(data: dict) -> None:
    tmp = SOUNDS_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(SOUNDS_JSON)  # atomic on the same filesystem

async def add_sound(
    display_name: str,
    file: discord.Attachment,
) -> None:
    if not _ID_RE.match(display_name):
        raise ValueError("Display Name must be lowercase letters/numbers/underscore/hyphen (≤64 chars).")
    if not file:
        raise ValueError("File is required.")

    with _lock:
        data, base_dir = load_sounds()
        sounds = data.get("sounds")
        for sound in sounds:
            if display_name in sound:
                raise ValueError(f"Display Name '{display_name}' already exists.")
        sounds.append({
            "id": int(sounds[-1]["id"]) + 1,
            "display_name": display_name,
            "file_name": file.filename
        })
        base_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_dir / f"{file.filename}"
        if file_path.exists():
            raise ValueError(f"File '{file_path}' already exists.")
        
        await file.save(file_path)
        save_index_atomic(data)

def delete_sound(sound_name: int) -> bool:
    with _lock:
        data, base_dir = load_sounds()
        sounds = data.get("sounds")
        entry = next(filter(lambda sound: sound['display_name'] == sound_name, sounds), None)
        if not entry:
            return False
        
        filename = entry.get("file_name")
        print(entry)
        file_path = (base_dir / filename)
        try:
            file_path.unlink()
        except Exception as e:
            raise ValueError(f"Failed to delete file: {e}")
        del sounds[sounds.index(entry)]
        save_index_atomic(data)
        return True

def list_sounds(prefix: str, limit: int = 25) -> List[Tuple[str,str]]:
    data, _ = load_sounds()
    sounds = data.get("sounds")
    soundValues = sounds[:limit]
    if not prefix:
        return soundValues
    p = prefix.lower()
    return filter(lambda sound: p in sound.display_name.lower(), soundValues)[:limit]