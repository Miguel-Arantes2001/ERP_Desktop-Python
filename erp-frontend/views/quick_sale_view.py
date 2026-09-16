from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QComboBox, QCheckBox,
    QDateEdit, QHeaderView,
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime

from services.sales import create_sale
from events import events


class QuickSaleView(QWidget):
    def __init__(self):
        super().__init__()
        self.cart = []
        self._next_item_id = 1

        layout = QVBoxLayout()

        title = QLabel("Venda rápida")
        title.setObjectName("title")
        layout.addWidget(title)

        hint = QLabel(
            "Use para lançar o caderno (ex.: ração cão R$ 17). "
            "Não cadastra produto e não altera estoque."
        )
        hint.setWordWrap(True)
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        form_layout = QHBoxLayout()

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Descrição (ex.: ração cão)")
        self.description_input.returnPressed.connect(self.add_item)
        form_layout.addWidget(self.description_input, 3)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Valor (ex.: 17)")
        self.price_input.returnPressed.connect(self.add_item)
        form_layout.addWidget(self.price_input, 1)

        add_button = QPushButton("Adicionar")
        add_button.clicked.connect(self.add_item)
        form_layout.addWidget(add_button)

        layout.addLayout(form_layout)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Descrição", "Valor"])
        self.table.setWordWrap(True)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.remove_button = QPushButton("Remover item selecionado")
        self.remove_button.setObjectName("secondary")
        self.remove_button.clicked.connect(self.remove_selected_item)
        layout.addWidget(self.remove_button)

        self.total_label = QLabel("Total: R$ 0,00")
        self.total_label.setAlignment(Qt.AlignRight)  # type: ignore
        layout.addWidget(self.total_label)

        layout.addWidget(QLabel("Forma de pagamento"))
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(
            ["dinheiro", "cartão de crédito", "cartão de débito", "pix"]
        )
        layout.addWidget(self.payment_combo)

        self.backdate_checkbox = QCheckBox("Registrar venda de outra data")
        self.backdate_checkbox.toggled.connect(self._toggle_sale_date)
        layout.addWidget(self.backdate_checkbox)

        sale_date_layout = QVBoxLayout()
        sale_date_layout.setContentsMargins(20, 0, 0, 0)
        self.sale_date_label = QLabel("Data da venda:")
        self.sale_date_input = QDateEdit()
        self.sale_date_input.setCalendarPopup(True)
        self.sale_date_input.setDisplayFormat("dd/MM/yyyy")
        self.sale_date_input.setDate(QDate.currentDate().addDays(-1))
        self.sale_date_input.setMaximumDate(QDate.currentDate())
        self.sale_date_label.setEnabled(False)
        self.sale_date_input.setEnabled(False)
        sale_date_layout.addWidget(self.sale_date_label)
        sale_date_layout.addWidget(self.sale_date_input)
        layout.addLayout(sale_date_layout)

        self.finish_button = QPushButton("Registrar venda rápida")
        self.finish_button.clicked.connect(self.finish_sale)
        layout.addWidget(self.finish_button)

        self.setLayout(layout)

    def _toggle_sale_date(self, checked: bool):
        self.sale_date_label.setEnabled(checked)
        self.sale_date_input.setEnabled(checked)

    def _get_selected_sale_datetime(self) -> datetime | None:
        if not self.backdate_checkbox.isChecked():
            return None

        qdate = self.sale_date_input.date()
        return datetime(
            qdate.year(),
            qdate.month(),
            qdate.day(),
            12,
            0,
            0,
        )

    def _parse_price(self, raw: str) -> float | None:
        text = raw.strip().replace("R$", "").replace(" ", "").replace(",", ".")
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
        if value <= 0:
            return None
        return value

    def add_item(self):
        description = self.description_input.text().strip()
        price = self._parse_price(self.price_input.text())

        if not description:
            QMessageBox.warning(self, "Aviso", "Informe a descrição do item.")
            self.description_input.setFocus()
            return

        if price is None:
            QMessageBox.warning(self, "Aviso", "Informe um valor válido maior que zero.")
            self.price_input.setFocus()
            return

        self.cart.append({
            "id": self._next_item_id,
            "name": description,
            "price": price,
            "quantity": 1,
        })
        self._next_item_id += 1
        self.description_input.clear()
        self.price_input.clear()
        self.description_input.setFocus()
        self.refresh_table()

    def remove_selected_item(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.cart):
            QMessageBox.warning(self, "Aviso", "Selecione um item para remover.")
            return
        self.cart.pop(row)
        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(0)
        total = 0.0

        for item in self.cart:
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(item["name"])
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # type: ignore
            name_item.setData(Qt.ItemDataRole.UserRole, item["id"])

            price_item = QTableWidgetItem(f"R$ {item['price']:.2f}")
            price_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # type: ignore

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, price_item)
            total += item["price"] * item["quantity"]

        self.total_label.setText(f"Total: R$ {total:.2f}")
        self.table.resizeRowsToContents()

    def finish_sale(self):
        if not self.cart:
            QMessageBox.warning(self, "Aviso", "Adicione pelo menos um item.")
            return

        items = [
            {
                "name": item["name"],
                "price": item["price"],
                "quantity": item["quantity"],
            }
            for item in self.cart
        ]
        payment_method = self.payment_combo.currentText()
        sold_at = self._get_selected_sale_datetime()
        sold_at_payload = sold_at.isoformat() if sold_at else None

        self.finish_button.setEnabled(False)
        self.finish_button.setText("Processando...")

        try:
            success = create_sale(items, payment_method, sold_at=sold_at_payload)
        finally:
            self.finish_button.setEnabled(True)
            self.finish_button.setText("Registrar venda rápida")

        if not success:
            QMessageBox.critical(self, "Erro", "Erro ao registrar a venda rápida.")
            return

        if sold_at:
            success_msg = f"Venda rápida registrada para {sold_at.strftime('%d/%m/%Y')}"
        else:
            success_msg = "Venda rápida registrada com sucesso"

        QMessageBox.information(self, "Sucesso", success_msg)
        events.sale_completed.emit()
        self.cart.clear()
        self.refresh_table()
        self.payment_combo.setCurrentIndex(0)
        self.backdate_checkbox.setChecked(False)
        self.sale_date_input.setDate(QDate.currentDate().addDays(-1))
        self.description_input.setFocus()
