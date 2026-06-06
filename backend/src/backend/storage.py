from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError

from .settings import Settings

ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def now_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def read_limited_upload(file: UploadFile, max_bytes: int) -> bytes:
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is larger than the configured upload limit.",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty.")
    return data


def sanitize_and_store_image(data: bytes, session_id: str, settings: Settings) -> Path:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = settings.upload_dir / f"{session_id}-{uuid4().hex}.raw"
    input_path.write_bytes(data)

    try:
        try:
            with Image.open(input_path) as image:
                image.load()
                image_format = image.format
                if image_format not in ALLOWED_FORMATS:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Only JPEG, PNG, and WebP images are supported.",
                    )
                if image.width < 32 or image.height < 32:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Image dimensions are too small to analyze.",
                    )

                sanitized = ImageOps.exif_transpose(image)
                if sanitized.mode not in ("RGB", "RGBA"):
                    sanitized = sanitized.convert("RGB")
                suffix = ALLOWED_FORMATS[image_format]
                output_path = settings.upload_dir / f"{session_id}-sanitized{suffix}"
                save_kwargs = {"quality": 92} if image_format in {"JPEG", "WEBP"} else {}
                sanitized.save(output_path, format=image_format, **save_kwargs)
                return output_path
        except UnidentifiedImageError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a decodable image.",
            ) from exc
    finally:
        input_path.unlink(missing_ok=True)


def delete_path(path_value: str | None) -> None:
    if not path_value:
        return
    Path(path_value).unlink(missing_ok=True)
