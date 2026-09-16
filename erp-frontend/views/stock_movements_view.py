from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,QHBoxLayout,QDateEdit,
    QHeaderView
)
from PySide6.QtCore import Qt,QDate
from datetime import datetime
from services.stock_movements import list_stock_movements
from PySide6.QtGui import QColor
from utils.units import format_quantity
from utils.product_display import name_tooltip
from events import events


class StockMovementsView(QWidget):
    def __init__(self):
        super().__init__()
        self._loaded = False
        events.sale_completed.connect(self._on_sale_completed)

        layout = QVBoxLayout(self)
        

        title = QLabel("Histórico de Movimentações de Estoque")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        filter_layout = QHBoxLayout()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        btn_filter = QPushButton("🔍 Filtrar")
        btn_filter.clicked.connect(self.load_data)

        filter_layout.addWidget(QLabel("De:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("Até:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(btn_filter)

        layout.addLayout(filter_layout)


        btn_reload = QPushButton("🔄 Atualizar")
        btn_reload.clicked.connect(self.load_data)
        layout.addWidget(btn_reload)

        self.table = QTableWidget(0, 5)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.setHorizontalHeaderLabels([
            "Produto", "Tipo", "Quantidade", "Motivo", "Data"
        ])
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        layout.addWidget(self.table)

    


    def load_data(self):
        self.table.setRowCount(0)

        start = self.start_date.date()
        end = self.end_date.date()
        start_iso = datetime(
            start.year(), start.month(), start.day(), 0, 0, 0
        ).isoformat()
        end_iso = datetime(
            end.year(), end.month(), end.day(), 23, 59, 59
        ).isoformat()

        movements = list_stock_movements(
            start_date=start_iso,
            end_date=end_iso,
        )

        for m in movements:
            row = self.table.rowCount()
            self.table.insertRow(row)

            tipo = "Entrada" if m["type"] == "in" else "Saída"

            product_name = m["product"].get("name", "")
            item_product = QTableWidgetItem(product_name)
            item_product.setToolTip(name_tooltip(product_name))
            self.table.setItem(row, 0, item_product)

            item_tipo = QTableWidgetItem(tipo)
            if m["type"] == "in":
                item_tipo.setForeground(QColor(0, 128, 0))  # darkGreen
            else:
                item_tipo.setForeground(QColor(255, 0, 0))  # darkRed

            self.table.setItem(row, 1, item_tipo)
            unit = m.get("product", {}).get("unit_of_measure", "un")
            qty_text = format_quantity(float(m["quantity"]), unit)
            self.table.setItem(row, 2, QTableWidgetItem(qty_text))
            self.table.setItem(row, 3, QTableWidgetItem(m.get("reason", "")))
            self.table.setItem(
                row, 4,
                QTableWidgetItem(m["created_at"].replace("T", " ")[:16])
            )

            for col in range(5):
                self.table.item(row, col).setFlags( # type: ignore
                    Qt.ItemIsSelectable | Qt.ItemIsEnabled # type: ignore
                )

        self.table.resizeRowsToContents()
        self._loaded = True

    def ensure_loaded(self):
        if not self._loaded:
            self.load_data()

    def _on_sale_completed(self):
        if self._loaded:
            self.load_data()
