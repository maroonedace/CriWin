"""FastAPI admin panel for managing soundboard sounds and cookies.

Reuses the Discord-free service layer. Protected by a single admin password
(HTTP Basic). Intended to bind loopback and be reached over an SSH/Tailscale
tunnel — run a single worker (the DB/storage clients are module-level singletons).
"""

import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from src.config import Config
from src.services.cookies import list_cookies, put_cookie
from src.services.soundboard import delete_sound, get_sounds, set_volume, upload_sound_file

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


def _find_file_name(name: str) -> str | None:
    for sound in get_sounds():
        if sound["name"] == name:
            return sound["file_name"]
    return None


def _redirect_home() -> RedirectResponse:
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/")
def index(request: Request, _: None = Depends(require_auth)):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"sounds": get_sounds(), "cookies": list_cookies()},
    )


@app.post("/sounds")
async def create_sound(
    name: str = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(require_auth),
):
    data = await file.read()
    try:
        await upload_sound_file(name, data, file.filename, file.content_type)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _redirect_home()


@app.post("/sounds/{name}/delete")
async def remove_sound(name: str, _: None = Depends(require_auth)):
    file_name = _find_file_name(name)
    if file_name is None:
        raise HTTPException(status_code=404, detail="Sound not found")
    try:
        await delete_sound(name, file_name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return _redirect_home()


@app.post("/sounds/{name}/volume")
def update_volume(name: str, volume: float = Form(...), _: None = Depends(require_auth)):
    set_volume(name, volume)
    return _redirect_home()


@app.post("/cookies")
async def upload_cookie(
    name: str = Form(...),
    file: UploadFile = File(...),
    _: None = Depends(require_auth),
):
    data = await file.read()
    put_cookie(name, data)
    return _redirect_home()
