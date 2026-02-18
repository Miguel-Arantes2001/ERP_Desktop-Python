from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,QHBoxLayout, QPushButton,QDateEdit
)
from PySide6.QtCore import Qt,QDate
from services.sales import list_sales
from datetime import datetime
from events  import events


class SalesView(QWidget):
    def __init__(self):
        super().__init__()
        events.sale_completed.connect(self.load_data) 
        self.limit= 20
        self.offset= 0
        self.start_date= None
        self.end_date= None
       

        layout = QVBoxLayout()

        filters_layout = QHBoxLayout()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        filter_btn = QPushButton("Filtrar")
        filter_btn.clicked.connect(self.apply_filter)

        filters_layout.addWidget(QLabel("De:"))
        filters_layout.addWidget(self.start_date)
        filters_layout.addWidget(QLabel("Até:"))
        filters_layout.addWidget(self.end_date)
        filters_layout.addWidget(filter_btn)

        layout.addLayout(filters_layout)



        title = QLabel("Histórico de Vendas")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Data", "Itens", "Pagamento", "Total"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(2, 160)

        layout.addWidget(self.table)
        self.setLayout(layout)
        self.limit = 20
        self.offset = 0

        buttons = QHBoxLayout()

        self.btn_prev = QPushButton("◀ Anterior")
        self.btn_next = QPushButton("Próxima ▶")

        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)

        buttons.addWidget(self.btn_prev)
        buttons.addWidget(self.btn_next)

        layout.addLayout(buttons)

        self.load_sales()
        self._loaded = True

    def load_sales(self):
        self.table.setRowCount(0)

        start_qdate = self.start_date.date() # type: ignore
        end_qdate = self.end_date.date() # type: ignore
        start_date = datetime(
        start_qdate.year(),
        start_qdate.month(),
        start_qdate.day(),
        0, 0, 0
        )

        end_date = datetime(
            end_qdate.year(),
            end_qdate.month(),
            end_qdate.day(),
            23, 59, 59
        )



        sales = list_sales(
            limit=self.limit,
            offset=self.offset,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        for sale in sales:
            row = self.table.rowCount()
            self.table.insertRow(row)

            created_at = sale.get("created_at")
            date_str = "-"

            if created_at:
                dt= datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            dt_local = dt.astimezone()
            date_str = dt_local.strftime("%d/%m/%Y %H:%M")

            total = f'{sale.get("total", 0):.2f}'
            payment = sale.get("payment_method", "-")

            items_count = sum(
                item["quantity"] for item in sale.get("items", [])
            )

            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            self.table.setItem(row, 1, QTableWidgetItem(str(items_count)))
            self.table.setItem(row, 2, QTableWidgetItem(payment))
            self.table.setItem(row, 3, QTableWidgetItem(total))

            for col in range(4):
                self.table.item(row, col).setFlags( # type: ignore
                    Qt.ItemIsSelectable | Qt.ItemIsEnabled # type: ignore
                )
    


    def next_page(self):
        self.offset += self.limit
        self.load_sales()

    def prev_page(self):
        if self.offset >= self.limit:
            self.offset -= self.limit
            self.load_sales()

    def apply_filter(self):
        self.offset = 0
        self.load_sales()

    def refresh(self):
        self.offset = 0
        self.load_sales()

    def load_data(self):
        self.load_sales()

