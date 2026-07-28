import uvicorn

from src.config import Config

if __name__ == "__main__":
    uvicorn.run(
        "src.web.app:app",
        host=Config.ADMIN_HOST,
        port=Config.ADMIN_PORT,
        workers=1,
    )
