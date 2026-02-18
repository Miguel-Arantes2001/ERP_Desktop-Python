from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton,QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
import requests
import requests
from services.auth import get_me


class Sidebar(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # =====================
        # LOGO DA LOJA
        # =====================
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter) # type: ignore
        self.logo_label.setFixedHeight(100)


        layout.addWidget(self.logo_label)

        self.dashboard_btn = QPushButton("Dashboard")
        self.pdv_btn = QPushButton("PDV")
        self.stock_btn = QPushButton("Estoque")
        self.stock_movements_btn = QPushButton("Movimentações")
        self.sales_btn = QPushButton("Vendas")

        layout.addWidget(self.dashboard_btn)
        layout.addWidget(self.pdv_btn)
        layout.addWidget(self.stock_btn)
        layout.addWidget(self.stock_movements_btn)
        layout.addWidget(self.sales_btn)

        layout.addStretch()

        self.setLayout(layout)
        self.setFixedWidth(180)



    def load_logo(self):
        me = get_me()
        if not me or "store" not in me:
            return

        store = me.get("store", {})
        logo_url = store.get("logo_url")

        if not logo_url:
            return

        try:
            response = requests.get(logo_url, timeout=5)
            if response.status_code != 200:
                return

            pixmap = QPixmap()
            pixmap.loadFromData(response.content)

            self.logo_label.setPixmap(
                pixmap.scaled(
                    140,
                    80,
                    Qt.KeepAspectRatio, # type: ignore
                    Qt.SmoothTransformation, # type: ignore
                )
            )
        except Exception as e:
            print("Erro ao carregar logo:", e)

    def load_data(self):
        self.load_logo()
