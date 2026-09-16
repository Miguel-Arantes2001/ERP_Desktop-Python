from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
import requests

from services.api import API_URL, get_headers
from services.products import create_photo_session
from utils.photo_qr import photo_upload_url, qr_pixmap


class ProductPhotoDialog(QDialog):
    def __init__(self, product: dict, parent=None):
        super().__init__(parent)
        self._product_id = product["id"]
        self._initial_image_path = product.get("image_path")
        self._photo_received = False

        name = (product.get("name") or "").strip()
        self.setWindowTitle("Adicionar foto")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(f"<b>{name}</b>")
        title.setWordWrap(True)
        layout.addWidget(title)

        hint = QLabel(
            "Celular e computador na mesma Wi-Fi. Escaneie o QR, "
            "tire a foto ou escolha da galeria. A miniatura aparece aqui quando chegar."
        )
        hint.setWordWrap(True)
        hint.setObjectName("chartCardHint")
        layout.addWidget(hint)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.qr_label)

        self.url_input = QLineEdit()
        self.url_input.setReadOnly(True)
        layout.addWidget(self.url_input)

        self.status_label = QLabel("Gerando QR...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        firewall_hint = QLabel(
            "Se a página não abrir no celular, no computador use:\n"
            "uvicorn main:app --reload --host 0.0.0.0 --port 8000\n"
            "e libere a porta 8000 no firewall do Windows."
        )
        firewall_hint.setWordWrap(True)
        font = QFont()
        font.setPointSize(8)
        firewall_hint.setFont(font)
        layout.addWidget(firewall_hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)  # type: ignore
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_photo)
        self._polls_left = 0

        session = create_photo_session(self._product_id)
        if not session or not session.get("token"):
            self.status_label.setText(
                "Não foi possível gerar o QR. Tente de novo."
            )
            return

        url = photo_upload_url(session["token"])
        self.url_input.setText(url)
        self.qr_label.setPixmap(qr_pixmap(url))
        self.status_label.setText("Aguardando foto do celular...")

        expires_in = int(session.get("expires_in") or 300)
        self._polls_left = max(expires_in // 2, 15)
        self._timer.start(2000)

    def _poll_photo(self):
        self._polls_left -= 1
        if self._polls_left <= 0:
            self._timer.stop()
            self.status_label.setText(
                "O QR expirou. Feche e abra de novo para gerar outro."
            )
            return

        product = self._fetch_product()
        if not product:
            return

        image_path = product.get("image_path")
        if image_path and image_path != self._initial_image_path:
            self._timer.stop()
            self._photo_received = True
            self.status_label.setText("Foto recebida. Pode fechar esta janela.")
            self.accept()

    def _fetch_product(self) -> dict | None:
        try:
            response = requests.get(
                f"{API_URL}/products/{self._product_id}",
                headers=get_headers(),
                timeout=5,
            )
        except requests.exceptions.RequestException:
            return None
        if not response.ok:
            return None
        return response.json()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)

    def photo_received(self) -> bool:
        return self._photo_received
