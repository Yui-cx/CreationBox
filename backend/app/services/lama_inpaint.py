import asyncio
import threading
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

from app.core.config import Settings


class LamaBusyError(Exception):
    pass


class LamaUnavailableError(Exception):
    pass


_lama_model = None
_lama_model_lock = threading.Lock()
_lama_task_lock = asyncio.Lock()


def is_lama_model_loading() -> bool:
    return _lama_model is None and _lama_model_lock.locked()


def _get_lama_model(settings: Settings):
    global _lama_model
    if _lama_model is not None:
        return _lama_model

    with _lama_model_lock:
        if _lama_model is not None:
            return _lama_model
        try:
            import torch
            from simple_lama_inpainting import SimpleLama
        except Exception as exc:
            raise LamaUnavailableError("LAMA_UNAVAILABLE") from exc

        if settings.inpaint_lama_device != "cpu":
            raise LamaUnavailableError("LAMA_UNAVAILABLE")

        try:
            torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
            _lama_model = SimpleLama(device=torch.device("cpu"))
        except Exception as exc:
            raise LamaUnavailableError("LAMA_UNAVAILABLE") from exc
        return _lama_model


async def preload_lama_model(settings: Settings) -> None:
    if not settings.inpaint_lama_enabled or not settings.inpaint_lama_preload:
        return
    await asyncio.to_thread(_get_lama_model, settings)


def _to_lama_image(source_bgr: np.ndarray) -> Image.Image:
    source_rgb = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(source_rgb).convert("RGB")


def _to_lama_mask(mask_gray: np.ndarray) -> Image.Image:
    _, binary_mask = cv2.threshold(mask_gray, 1, 255, cv2.THRESH_BINARY)
    return Image.fromarray(binary_mask).convert("L")


def _run_lama_sync(source_bgr: np.ndarray, mask_gray: np.ndarray, settings: Settings) -> bytes:
    model = _get_lama_model(settings)
    image = _to_lama_image(source_bgr)
    mask = _to_lama_mask(mask_gray)
    try:
        result = model(image, mask).convert("RGB")
    except LamaUnavailableError:
        raise
    except Exception as exc:
        raise RuntimeError("INPAINT_FAILED") from exc

    buffer = BytesIO()
    result.save(buffer, format="PNG")
    return buffer.getvalue()


async def inpaint_with_lama(source_bgr: np.ndarray, mask_gray: np.ndarray, settings: Settings) -> bytes:
    if not settings.inpaint_lama_enabled:
        raise LamaUnavailableError("LAMA_UNAVAILABLE")

    if settings.inpaint_lama_concurrency != 1:
        raise LamaUnavailableError("LAMA_UNAVAILABLE")

    if is_lama_model_loading():
        raise LamaBusyError("LAMA_BUSY")

    if _lama_task_lock.locked():
        raise LamaBusyError("LAMA_BUSY")

    # CPU LaMa is intentionally serialized to protect low-spec deployments.
    await _lama_task_lock.acquire()
    try:
        return await asyncio.to_thread(_run_lama_sync, source_bgr, mask_gray, settings)
    finally:
        _lama_task_lock.release()
