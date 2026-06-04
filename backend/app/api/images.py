import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models.entities import User
from app.services.lama_inpaint import LamaBusyError, LamaUnavailableError, inpaint_with_lama


router = APIRouter(prefix="/images", tags=["images"])

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
DEFAULT_INPAINT_RADIUS = 5
IMAGE_ENGINES = {"opencv", "lama"}


def _ensure_supported_file(file: UploadFile, field_name: str) -> None:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="INVALID_MASK" if field_name == "mask" else "UNSUPPORTED_IMAGE_TYPE",
        )


def _decode_image(data: bytes, mode: int, error_code: str) -> np.ndarray:
    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, mode)
    if image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_code)
    return image


def _to_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def _prepare_inpaint_mask(mask_gray: np.ndarray, radius: int) -> np.ndarray:
    _, binary_mask = cv2.threshold(mask_gray, 1, 255, cv2.THRESH_BINARY)
    if int(np.count_nonzero(binary_mask)) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_MASK")

    close_kernel_size = 3 if radius < 5 else 5
    close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel_size, close_kernel_size))
    closed_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, close_kernel, iterations=1)

    dilate_size = max(3, min(radius * 2 + 1, 15))
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_size, dilate_size))
    dilated_mask = cv2.dilate(closed_mask, dilate_kernel, iterations=1)

    blurred_mask = cv2.GaussianBlur(dilated_mask, (3, 3), 0)
    _, prepared_mask = cv2.threshold(blurred_mask, 16, 255, cv2.THRESH_BINARY)
    return prepared_mask


@router.post("/inpaint")
async def inpaint_image(
    current_user: User = Depends(get_current_user),
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    engine: str = Form("opencv"),
    method: str = Form("telea"),
    radius: int = Form(DEFAULT_INPAINT_RADIUS),
):
    _ = current_user
    _ensure_supported_file(image, "image")
    _ensure_supported_file(mask, "mask")
    if engine not in IMAGE_ENGINES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="VALIDATION_ERROR")
    if engine == "opencv" and method not in {"telea", "ns"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="VALIDATION_ERROR")
    if radius < 1 or radius > 10:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="VALIDATION_ERROR")

    settings = get_settings()
    max_image_bytes = settings.inpaint_lama_max_image_bytes if engine == "lama" else MAX_IMAGE_BYTES
    image_bytes = await image.read()
    mask_bytes = await mask.read()
    if len(image_bytes) > max_image_bytes or len(mask_bytes) > max_image_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="IMAGE_TOO_LARGE")

    source = _to_bgr(_decode_image(image_bytes, cv2.IMREAD_UNCHANGED, "INVALID_IMAGE"))
    mask_gray = _decode_image(mask_bytes, cv2.IMREAD_GRAYSCALE, "INVALID_MASK")
    if source.shape[:2] != mask_gray.shape[:2]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_MASK")
    if engine == "lama" and source.shape[0] * source.shape[1] > settings.inpaint_lama_max_pixels:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="IMAGE_TOO_LARGE")

    prepared_mask = _prepare_inpaint_mask(mask_gray, radius)
    if engine == "lama":
        try:
            content = await inpaint_with_lama(source, prepared_mask, settings)
        except LamaBusyError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="LAMA_BUSY") from exc
        except LamaUnavailableError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LAMA_UNAVAILABLE") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="INPAINT_FAILED") from exc
        return Response(content=content, media_type="image/png")

    algorithm = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    try:
        result = cv2.inpaint(source, prepared_mask, float(radius), algorithm)
        ok, encoded = cv2.imencode(".png", result)
    except cv2.error as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="INPAINT_FAILED") from exc
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="INPAINT_FAILED")

    return Response(content=encoded.tobytes(), media_type="image/png")
