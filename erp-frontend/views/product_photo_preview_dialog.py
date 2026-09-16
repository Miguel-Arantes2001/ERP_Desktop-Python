from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt

from services.products import rotate_product_photo
from utils.product_images import invalidate_photo_cache, load_product_photo


class ProductPhotoPreviewDialog(QDialog):
    def __init__(self, product: dict, parent=None):
        super().__init__(parent)
        self.replace_requested = False
        self.photo_changed = False
        self._product = product
        name = (product.get("name") or "").strip()
        self.setWindowTitle(name or "Foto do produto")
        self.setMinimumSize(520, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"<b>{name}</b>")
        title.setWordWrap(True)
        layout.addWidget(title)

        self.photo_label = QLabel()
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_label.setMinimumSize(480, 480)
        layout.addWidget(self.photo_label, stretch=1)

        hint = QLabel(
            "Se a foto estiver deitada, use Girar. "
        
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QHBoxLayout()
        btn_rotate = QPushButton("Girar")
        btn_rotate.clicked.connect(self._rotate)
        btn_replace = QPushButton("Trocar foto")
        btn_replace.clicked.connect(self._request_replace)
        btn_close = QPushButton("Fechar")
        btn_close.clicked.connect(self.reject)
        buttons.addWidget(btn_rotate)
        buttons.addStretch()
        buttons.addWidget(btn_replace)
        buttons.addWidget(btn_close)
        layout.addLayout(buttons)

        self._show_photo(product.get("image_path"))

    def _show_photo(self, image_path: str | None):
        pixmap = load_product_photo(image_path)
        if pixmap is None or pixmap.isNull():
            self.photo_label.clear()
            self.photo_label.setText("Não foi possível carregar a foto.")
            return
        scaled = pixmap.scaled(
            720,
            720,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.photo_label.setText("")
        self.photo_label.setPixmap(scaled)

    def closeEvent(self, event):
        self.photo_label.clear()
        super().closeEvent(event)

    def _rotate(self):
        old_path = self._product.get("image_path")
        updated = rotate_product_photo(self._product["id"])
        if not updated:
            return
        invalidate_photo_cache(old_path)
        self._product = updated
        self.photo_changed = True
        self._show_photo(updated.get("image_path"))

    def _request_replace(self):
        self.replace_requested = True
        self.accept()
