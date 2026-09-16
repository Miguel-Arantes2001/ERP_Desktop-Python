from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QPushButton, QDateEdit,
    QDialog, QHeaderView
)
from PySide6.QtCore import Qt, QDate
from services.sales import list_sales
from datetime import datetime
from events  import events
from utils.units import format_quantity, format_unit_price


class SalesView(QWidget):
    def __init__(self):
        super().__init__()
        events.sale_completed.connect(self._on_sale_completed) 
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
            ["Data", "Produtos", "Pagamento", "Total"]
        )
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setToolTip("Dê um duplo-clique numa venda para ver o detalhe completo")
        self.table.cellDoubleClicked.connect(self.show_sale_detail)

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

        self._loaded = False

    def ensure_loaded(self):
        if not self._loaded:
            self.load_data()

    def _on_sale_completed(self):
        if self._loaded:
            self.load_data()

    def load_sales(self):
        self.table.setRowCount(0)

        start_qdate = self.start_date.date() 
        end_qdate = self.end_date.date() 
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

            items = sale.get("items", [])
            products_summary = self._build_products_summary(items)
            all_names = [self._item_display_name(item) for item in items]

            products_item = QTableWidgetItem(products_summary)
            products_item.setToolTip("\n".join(all_names) if all_names else products_summary)
            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            self.table.setItem(row, 1, products_item)
            self.table.setItem(row, 2, QTableWidgetItem(payment))
            self.table.setItem(row, 3, QTableWidgetItem(total))

            
            self.table.item(row, 1).setData(Qt.ItemDataRole.UserRole, sale)

            for col in range(4):
                self.table.item(row, col).setFlags( # type: ignore
                    Qt.ItemIsSelectable | Qt.ItemIsEnabled # type: ignore
                )

        self.table.resizeRowsToContents()

    @staticmethod
    def _item_display_name(item: dict) -> str:
        name = item.get("product_name") or item.get("description")
        if not name:
            return "Produto removido"
        if item.get("product_id") is None or item.get("item_type") == "generic":
            return f"{name} (rápida)"
        return name

    @staticmethod
    def _build_products_summary(items: list) -> str:
        if not items:
            return "-"

        names = [SalesView._item_display_name(item) for item in items]

        if len(names) <= 2:
            return ", ".join(names)

        return f"{names[0]}, {names[1]} e mais {len(names) - 2}"

    def show_sale_detail(self, row: int, _column: int):
        cell = self.table.item(row, 1)
        if cell is None:
            return

        sale = cell.data(Qt.ItemDataRole.UserRole)
        if not sale:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Venda #{sale.get('id', '-')}")
        dialog.resize(560, 380)

        layout = QVBoxLayout(dialog)

        header = QLabel(
            f"Pagamento: {sale.get('payment_method', '-')}    "
            f"Total: R$ {sale.get('total', 0):.2f}"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        items_table = QTableWidget(0, 3)
        items_table.setHorizontalHeaderLabels(["Produto", "Qtd", "Preço unit."])
        items_table.setWordWrap(True)
        items_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        items_header = items_table.horizontalHeader()
        items_header.setStretchLastSection(False)
        items_header.setSectionResizeMode(0, QHeaderView.Stretch)
        items_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        items_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        items_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        items_table.setEditTriggers(QTableWidget.NoEditTriggers)  # type: ignore

        for item in sale.get("items", []):
            r = items_table.rowCount()
            items_table.insertRow(r)
            unit = item.get("unit_of_measure", "un")
            qty = item.get("quantity", 0)
            product_name = SalesView._item_display_name(item)
            name_item = QTableWidgetItem(product_name)
            name_item.setToolTip(product_name)
            items_table.setItem(r, 0, name_item)
            items_table.setItem(r, 1, QTableWidgetItem(format_quantity(qty, unit)))
            price_text = format_unit_price(item.get("price", 0), unit)
            items_table.setItem(r, 2, QTableWidgetItem(price_text))

        items_table.resizeRowsToContents()
        layout.addWidget(items_table)
        dialog.setLayout(layout)
        dialog.exec()
    


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
        self._loaded = True

