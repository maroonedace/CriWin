"""FastAPI admin panel for managing soundboard sounds and cookies.

Reuses the Discord-free service layer. Protected by a single admin password
(HTTP Basic). Intended to bind loopback and be reached over an SSH/Tailscale
tunnel — run a single worker (the DB/storage clients are module-level singletons).
"""

import secrets
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from src.config import Config
from src.services.cookies import (
    COOKIE_PLATFORM_LABELS,
    SUPPORTED_COOKIE_PLATFORMS,
    list_cookies,
    put_cookie,
)
from src.services.soundboard import (
    delete_sound,
    get_guilds,
    get_sounds,
    rename_sound,
    set_volume,
    upload_sound_file,
)
from src.services.soundboard.validation import (
    DUPLICATE_NAME_MESSAGE,
    INVALID_NAME_MESSAGE,
    is_valid_name,
)

app = FastAPI(title="Criwin Admin")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    """Validate the admin username + password (constant-time).

    Both are read from the environment (``ADMIN_USERNAME`` / ``ADMIN_PASSWORD``) and
    must be set and match. Comparisons are done on UTF-8 bytes so non-ASCII input can
    never raise (``secrets.compare_digest`` rejects non-ASCII ``str``), and both fields
    are always compared to keep the check constant-time and avoid leaking which was
    wrong. A mismatch returns 401 (re-prompting the browser), never a 500.
    """
    username = Config.ADMIN_USERNAME
    password = Config.ADMIN_PASSWORD

    user_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"), (username or "").encode("utf-8")
    )
    pass_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"), (password or "").encode("utf-8")
    )

    if not (username and password and user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


def _require_guild(guild_id: int) -> int:
    """Reject a guild the bot is not in, so sounds can't be filed under a stray id.

    The guild list comes from the ``guilds`` table the bot maintains; this process has
    no Discord token of its own.
    """
    if not any(guild["guild_id"] == guild_id for guild in get_guilds()):
        raise HTTPException(status_code=404, detail="Unknown server")
    return guild_id


def _find_file_name(guild_id: int, name: str) -> str | None:
    for sound in get_sounds(guild_id):
        if sound["name"] == name:
            return sound["file_name"]
    return None


def _validate_name(name: str, sounds: list[dict[str, Any]], current: str | None = None) -> None:
    """Enforce the shared display-name rules for create/rename.

    Raises HTTP 400 on an invalid format or a name already taken by another sound.
    ``current`` is the sound being renamed, so renaming to its own name is not a
    false duplicate.
    """
    if not is_valid_name(name):
        raise HTTPException(status_code=400, detail=INVALID_NAME_MESSAGE)
    if any(sound["name"] == name and sound["name"] != current for sound in sounds):
        raise HTTPException(status_code=400, detail=DUPLICATE_NAME_MESSAGE)


def _redirect_home(guild_id: int | None = None) -> RedirectResponse:
    """Back to the index, keeping the selected server."""
    target = "/" if guild_id is None else f"/?guild_id={guild_id}"
    return RedirectResponse(target, status_code=status.HTTP_303_SEE_OTHER)


@app.get("/")
def index(request: Request, guild_id: int | None = None, _: None = Depends(require_auth)):
    stored = set(list_cookies())
    cookie_platforms = [
        {"name": platform, "label": COOKIE_PLATFORM_LABELS[platform], "is_set": platform in stored}
        for platform in SUPPORTED_COOKIE_PLATFORMS
    ]

    # Sounds belong to one server, so the page always works against a selected one:
    # the requested server if the bot is in it, else the first known server.
    guilds = get_guilds()
    known_ids = {guild["guild_id"] for guild in guilds}
    selected = guild_id if guild_id in known_ids else (guilds[0]["guild_id"] if guilds else None)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "guilds": guilds,
            "selected_guild_id": selected,
            "sounds": get_sounds(selected) if selected is not None else [],
            "cookie_platforms": cookie_platforms,
        },
    )


@app.post("/sounds")
async def create_sound(
    guild_id: int = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(require_auth),
):
    _require_guild(guild_id)
    _validate_name(name, get_sounds(guild_id))
    data = await file.read()
    try:
        await upload_sound_file(guild_id, name, data, file.filename, file.content_type)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _redirect_home(guild_id)


@app.post("/sounds/{name}/delete")
async def remove_sound(name: str, guild_id: int = Form(...), _: None = Depends(require_auth)):
    _require_guild(guild_id)
    file_name = _find_file_name(guild_id, name)
    if file_name is None:
        raise HTTPException(status_code=404, detail="Sound not found")
    try:
        await delete_sound(guild_id, name, file_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _redirect_home(guild_id)


@app.post("/sounds/{name}/rename")
def rename(
    name: str,
    guild_id: int = Form(...),
    new_name: str = Form(...),
    _: None = Depends(require_auth),
):
    _require_guild(guild_id)
    sounds = get_sounds(guild_id)
    if not any(sound["name"] == name for sound in sounds):
        raise HTTPException(status_code=404, detail="Sound not found")
    _validate_name(new_name, sounds, current=name)
    try:
        rename_sound(guild_id, name, new_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _redirect_home(guild_id)


@app.post("/sounds/{name}/volume")
def update_volume(
    name: str,
    guild_id: int = Form(...),
    volume: float = Form(...),
    _: None = Depends(require_auth),
):
    _require_guild(guild_id)
    set_volume(guild_id, name, volume)
    return _redirect_home(guild_id)


@app.post("/cookies/{platform}")
async def upload_cookie(
    platform: str,
    file: UploadFile = File(...),
    guild_id: int | None = Form(None),
    _: None = Depends(require_auth),
):
    # Cookies are global; guild_id only carries the page's server selection through
    # the redirect.
    if platform not in SUPPORTED_COOKIE_PLATFORMS:
        raise HTTPException(status_code=404, detail="Unknown platform")
    data = await file.read()
    put_cookie(platform, data)
    return _redirect_home(guild_id)
