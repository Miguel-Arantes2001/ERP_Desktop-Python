import socket
from io import BytesIO
from urllib.parse import quote, urlparse

import qrcode
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from services.api import API_URL


def get_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def api_port() -> int:
    parsed = urlparse(API_URL)
    if parsed.port:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def photo_upload_url(token: str) -> str:
    encoded = quote(token, safe=".-_")
    return f"http://{get_lan_ip()}:{api_port()}/photo/{encoded}"


def qr_pixmap(url: str, size: int = 280) -> QPixmap:
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue())
    return pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
