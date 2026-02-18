from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QDateEdit, QFrame
)
from PySide6.QtCore import Qt, QDate
from services.reports import (
    get_sales_summary,
    get_top_products
)



class DashboardView(QWidget):
    def __init__(self):
        super().__init__()
        

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # =========================
        # FILTRO DE DATA
        # =========================
        filter_layout = QHBoxLayout()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        btn_filter = QPushButton("Aplicar filtro")
        btn_filter.clicked.connect(self.load_data)

        filter_layout.addWidget(QLabel("De:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("Até:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(btn_filter)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # =========================
        # CARD TOTAL VENDIDO
        # =========================
        self.total_card = QFrame()
        # self.total_card.setFrameShape(QFrame.StyledPanel) # type: ignore
        # self.total_card.setStyleSheet("""
        #     QFrame {
        #         background-color: #f5f7fa;
        #         border-radius: 12px;
        #         border: 1px solid #dce1e7;
        #     }
        # """)
        self.total_card.setObjectName("totalCard")

        card_layout = QVBoxLayout(self.total_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(8)

        card_title = QLabel("Total vendido no período")
        card_title.setStyleSheet("font-size: 14px; color: #666;")

        self.total_label = QLabel("R$ 0,00")
        self.total_label.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #2e7d32;
        """)

        card_layout.addWidget(card_title)
        card_layout.addWidget(self.total_label)

        

        layout.addWidget(self.total_card)
        layout.setSpacing(16)

        # =========================
        # TOP PRODUTOS
        # =========================
        title = QLabel("Produtos mais vendidos")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.products_table = QTableWidget(0, 2)
        self.products_table.setHorizontalHeaderLabels(
            ["Produto", "Quantidade vendida"]
        )
        self.products_table.horizontalHeader().setStretchLastSection(True)
        self.products_table.setEditTriggers(QTableWidget.NoEditTriggers) # type: ignore
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows) # type: ignore

        layout.addWidget(self.products_table)


    def load_data(self):

        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")

        # ===== TOTAL =====
        summary = get_sales_summary(start, end)
        total = summary.get("total_sales", 0)

        self.total_label.setText(f"R$ {total:,.2f}".replace(",", "."))

        # ===== TOP PRODUTOS =====
        products = get_top_products()
        self.products_table.setRowCount(0)

        for item in products:
            row = self.products_table.rowCount()
            self.products_table.insertRow(row)
            self.products_table.setItem(
                row, 0, QTableWidgetItem(item["product"])
            )
            self.products_table.setItem(
                row, 1, QTableWidgetItem(str(item["quantity_sold"]))
            )

    def showEvent(self, event):
        self.load_data()
        super().showEvent(event)

