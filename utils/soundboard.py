import re
import json
import threading
from pathlib import Path
from typing import Dict, Tuple, List

import discord

# Regular expression for validating sound IDs
ID_RE = re.compile(r"^[a-zA-Z0-9 _-]{1,64}$")

# Define the location of the JSON file
SOUNDS_JSON = Path("./sounds/sounds.json")

# Lock to ensure thread-safety
_lock = threading.Lock()

# Global cache and settings
_cache: Dict[str, str] = {}
_cache_mtime: float = -1.0
_base_dir = Path("./sounds")

allowed_content_types = {'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/flac', 'audio/aac'}

def load_sounds() -> Tuple[Dict[str, List], Path]:
    global _cache, _cache_mtime, _base_dir
    # Ensure the 'sounds' directory exists
    if not _base_dir.exists():
        _base_dir.mkdir(parents=True, exist_ok=True)
    
    if not SOUNDS_JSON.exists():
        # Create the directory if it doesn't exist (redundant, but safe)
        SOUNDS_JSON.parent.mkdir(parents=True, exist_ok=True)

        # Create the JSON file with the default content
        with open(SOUNDS_JSON, 'w', encoding='utf-8') as f:
            json.dump({"sounds": []}, f)

        _cache = {"sounds": []}
        _cache_mtime = -1.0
        return _cache, _base_dir

    try:
        mtime = SOUNDS_JSON.stat().st_mtime
    except Exception as e:
        print(f"Error getting file stats: {e}")
        return _cache, _base_dir

    if mtime != _cache_mtime:
        try:
            data = json.loads(SOUNDS_JSON.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Error reading JSON file: {e}")
            return _cache, _base_dir
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
    if not ID_RE.match(display_name):
        raise ValueError("Display Name must be less than 64 characters.")
    if not file:
        raise ValueError("File is required.")
    if file.content_type not in allowed_content_types:
        raise ValueError("Only audio files are allowed (Ex. .mp3, .wav, etc.).")

    with _lock:
        data, base_dir = load_sounds()
        sounds = data.get("sounds", [])
        for sound in sounds:
            if display_name in sound:
                raise ValueError(f"Display Name '{display_name}' already exists.")
        sound_id = 1 if not sounds else int(sounds[-1]["id"]) + 1
        sounds.append({
            "id": sound_id,
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
    if not sounds:
        return []
    soundValues = sounds[:limit]
    if not prefix:
        return soundValues
    p = prefix.lower()
    return filter(lambda sound: p in sound.display_name.lower(), soundValues)[:limit]