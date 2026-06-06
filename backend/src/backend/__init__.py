from .app import app


def main() -> None:
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)


__all__ = ["app", "main"]
