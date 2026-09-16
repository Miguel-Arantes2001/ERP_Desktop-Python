import requests
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap

from services.api import API_URL

_icon_cache: dict[tuple[str, int], QIcon] = {}
_placeholder_icons: dict[int, QIcon] = {}
_failed_paths: set[str] = set()


def invalidate_photo_cache(image_path: str | None = None) -> None:
    if image_path is None:
        _icon_cache.clear()
        _failed_paths.clear()
        return

    _failed_paths.discard(image_path)
    for key in [k for k in _icon_cache if k[0] == image_path]:
        del _icon_cache[key]


def placeholder_photo_icon(size: int = 48) -> QIcon:
    cached = _placeholder_icons.get(size)
    if cached is not None:
        return cached
    pix = QPixmap(size, size)
    pix.fill(QColor("#E5E7EB"))
    icon = QIcon(pix)
    _placeholder_icons[size] = icon
    return icon


def has_cached_photo_icon(image_path: str | None, size: int = 48) -> bool:
    if not image_path:
        return True
    return (image_path, size) in _icon_cache


def _download_pixmap(image_path: str) -> QPixmap | None:
    if image_path in _failed_paths:
        return None

    url = f"{API_URL}/static/{image_path.lstrip('/')}"
    try:
        response = requests.get(url, timeout=5)
    except requests.exceptions.RequestException:
        _failed_paths.add(image_path)
        return None
    if not response.ok:
        _failed_paths.add(image_path)
        return None
    pixmap = QPixmap()
    if not pixmap.loadFromData(response.content):
        _failed_paths.add(image_path)
        return None
    return pixmap


def load_product_photo(image_path: str | None) -> QPixmap | None:
    if not image_path:
        return None
    return _download_pixmap(image_path)


def get_product_photo_icon(image_path: str | None, size: int = 48) -> QIcon:
    if not image_path:
        return placeholder_photo_icon(size)

    key = (image_path, size)
    cached = _icon_cache.get(key)
    if cached is not None:
        return cached

    photo = _download_pixmap(image_path)
    if photo is None or photo.isNull():
        icon = placeholder_photo_icon(size)
        _icon_cache[key] = icon
        return icon

    scaled = photo.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    icon = QIcon(scaled)
    _icon_cache[key] = icon
    return icon
