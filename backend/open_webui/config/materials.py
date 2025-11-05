import os


def _read_backend() -> str:
    value = os.environ.get("MATERIAL_STORAGE_BACKEND", "local").strip().lower()
    if value not in {"local", "ffmpeg"}:
        raise ValueError(
            "MATERIAL_STORAGE_BACKEND must be one of {'local', 'ffmpeg'}, "
            f"got '{value}'"
        )
    return value


MATERIAL_STORAGE_BACKEND = _read_backend()
USE_FFMPEG_BACKEND = MATERIAL_STORAGE_BACKEND == "ffmpeg"

