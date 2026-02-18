from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,QHBoxLayout,QDateEdit
)
from PySide6.QtCore import Qt,QDate
from services.stock_movements import list_stock_movements
from PySide6.QtGui import QColor


class StockMovementsView(QWidget):
    def __init__(self):
        super().__init__()

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

        self.table.setColumnWidth(0, 180)  # Produto
        self.table.setColumnWidth(1, 80)   # Tipo
        self.table.setColumnWidth(2, 90)   # Quantidade
        self.table.setColumnWidth(3, 350)  # Motivo 
        self.table.setColumnWidth(4, 140)  # Data

        self.table.setHorizontalHeaderLabels([
            "Produto", "Tipo", "Quantidade", "Motivo", "Data"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

    


    def load_data(self):
        self.table.setRowCount(0)

        movements = list_stock_movements()

        start=self.start_date.date()
        end=self.end_date.date()

        for m in movements:
            row = self.table.rowCount()
            self.table.insertRow(row)

            date_only = QDate.fromString(m["created_at"][:10], "yyyy-MM-dd")
            if date_only < start or date_only > end:
                continue

            tipo = "Entrada" if m["type"] == "in" else "Saída"

            self.table.setItem(row, 0, QTableWidgetItem(m["product"].get("name", "")))

            item_tipo = QTableWidgetItem(tipo)
            if m["type"] == "in":
                item_tipo.setForeground(QColor(0, 128, 0))  # darkGreen
            else:
                item_tipo.setForeground(QColor(255, 0, 0))  # darkRed

            self.table.setItem(row, 1, item_tipo)
            self.table.setItem(row, 2, QTableWidgetItem(str(m["quantity"])))
            self.table.setItem(row, 3, QTableWidgetItem(m.get("reason", "")))
            self.table.setItem(
                row, 4,
                QTableWidgetItem(m["created_at"].replace("T", " ")[:16])
            )

            for col in range(5):
                self.table.item(row, col).setFlags( # type: ignore
                    Qt.ItemIsSelectable | Qt.ItemIsEnabled # type: ignore
                )

    def showEvent(self, event):
        self.load_data()
        super().showEvent(event)
