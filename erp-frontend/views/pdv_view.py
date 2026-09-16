from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QListWidget, QListWidgetItem, QCheckBox, QComboBox, QDateEdit,
    QHeaderView
)
from PySide6.QtCore import Qt, QDate, QTimer
from services.sales import create_sale

from services.products import get_product_by_barcode, search_products, create_product
from views.stock_view import AddProductDialog
from views.fractional_quantity_dialog import FractionalQuantityDialog
from utils.printer import print_receipt
from datetime import datetime
from events import events
from services.auth_front import get_me
from utils.units import (
    format_quantity,
    format_quantity_value,
    format_unit_price,
    is_fractional_unit,
    unit_suffix,
)
from utils.product_display import (
    clean_description,
    name_tooltip,
    name_with_description,
)


class PDVView(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Código de barras"))

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Digite ou escaneie o código de barras")
        self.barcode_input.returnPressed.connect(self.add_item_by_barcode)
        layout.addWidget(self.barcode_input)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar produto pelo nome")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._run_name_search)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        layout.addWidget(self.search_input)

        self.results_list = QListWidget()
        self.results_list.setWordWrap(True)
        self.results_list.setMaximumHeight(280)
        self.results_list.itemClicked.connect(self.add_product_from_search)
        layout.addWidget(self.results_list)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Produto", "Qtd", "+", "-", "Preço", ""])
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 40)
        self.table.setColumnWidth(3, 40)
        self.table.setColumnWidth(5, 0)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.remove_button = QPushButton("Remover item selecionado")
        self.remove_button.clicked.connect(self.remove_selected_item)
        layout.addWidget(self.remove_button)

        self.total_label = QLabel("Total: R$ 0,00")
        self.total_label.setAlignment(Qt.AlignRight)  # type: ignore
        layout.addWidget(self.total_label)

        self.print_checkbox = QCheckBox("Imprimir recibo")
        self.print_checkbox.setChecked(False)
        layout.addWidget(self.print_checkbox)

        layout.addWidget(QLabel("Forma de pagamento"))

        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["dinheiro", "cartão de crédito", "cartão de débito", "pix"])
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

        self.finish_button = QPushButton("Finalizar venda")
        self.finish_button.clicked.connect(self.finish_sale)
        layout.addWidget(self.finish_button)

        self.setLayout(layout)
        self.cart = {}

        self.table.itemChanged.connect(self.on_qty_changed)  

        self.total = 0.0

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

    def on_qty_changed(self, item):
        if item.column() != 1:
            return

        row = item.row()
        name_item = self.table.item(row, 0)

        if not name_item:
            return

        product_id = name_item.data(Qt.ItemDataRole.UserRole)
        data = self.cart.get(product_id)

        if not data:
            return

        unit = data.get("unit", "un")

        try:
            qty = float(item.text().replace(",", "."))
        except ValueError:
            self.refresh_table()
            return

        stock = data.get("stock")

        
        if stock is not None and qty > stock:

            QMessageBox.warning(
                self,
                "Estoque insuficiente",
                f"Estoque disponível: {format_quantity(stock, unit)}"
            )

            self.refresh_table()
            return

        if qty <= 0:
            del self.cart[product_id]
        else:
            self.cart[product_id]["qty"] = qty

        self.refresh_table()


    def remove_selected_item(self):
        row = self.table.currentRow()
        if row < 0:
            return

        name_item = self.table.item(row, 0)
        if not name_item:
            return

        product_id = name_item.data(Qt.ItemDataRole.UserRole)
        self.cart.pop(product_id, None)

        self.refresh_table()

    def _add_product_to_cart(
        self,
        product,
        quantity: float | None = None
    ) -> bool:

        product_id = product["id"]

        unit = product.get(
            "unit_of_measure",
            "un"
        )

        stock_value = product.get("stock")

        if stock_value is None:
            stock = None
        else:
            stock = float(stock_value)

        nome_padronizado = product["name"].strip().title()

        if is_fractional_unit(unit):

            if quantity is None:

                dialog = FractionalQuantityDialog(
                    product,
                    self
                )

                if not dialog.exec():
                    return False

                quantity = dialog.get_quantity()

            current_qty = self.cart.get(
                product_id,
                {}
            ).get("qty", 0)

            new_qty = current_qty + quantity

            
            if stock is not None and new_qty > stock:

                QMessageBox.warning(
                    self,
                    "Estoque insuficiente",
                    f"Estoque disponível: "
                    f"{format_quantity(stock, unit)}"
                )

                return False

            if product_id in self.cart:

                self.cart[product_id]["qty"] = new_qty

            else:

                self.cart[product_id] = {
                    "name": nome_padronizado,
                    "price": product["price"],
                    "qty": quantity,
                    "stock": stock,
                    "unit": unit,
                    "description": clean_description(product.get("description")),
                }

        else:

            current_qty = self.cart.get(
                product_id,
                {}
            ).get("qty", 0)

            new_qty = current_qty + 1

            if stock is not None and new_qty > stock:

                QMessageBox.warning(
                    self,
                    "Estoque insuficiente",
                    f"Estoque disponível: "
                    f"{format_quantity(stock, unit)}"
                )

                return False

            if product_id in self.cart:

                self.cart[product_id]["qty"] += 1

            else:

                self.cart[product_id] = {
                    "name": nome_padronizado,
                    "price": product["price"],
                    "qty": 1,
                    "stock": stock,
                    "unit": unit,
                    "description": clean_description(product.get("description")),
                }

        self.refresh_table()

        return True


    def _quick_register_product(
        self,
        prefill_barcode: str = "",
        prefill_name: str = ""
    ):
        dialog = AddProductDialog(self)

        dialog.barcode_input.setText(prefill_barcode)
        dialog.name_input.setText(prefill_name)
        if prefill_barcode:
            dialog.no_barcode_checkbox.setEnabled(False)

        if not dialog.exec():
            return

        data = dialog.get_data()

        

        if not data["name"].strip():
            QMessageBox.warning(
                self,
                "Erro",
                "Preencha o nome do produto"
            )
            return

        if not data.get("without_barcode") and not data.get("barcode", "").strip():
            QMessageBox.warning(
                self,
                "Erro",
                "Informe o código de barras ou marque "
                "'Cadastrar sem código de barras por enquanto'."
            )
            return

        stock = data.get("quantity")

        if stock is not None and stock < 0:
            QMessageBox.warning(
                self,
                "Erro",
                "Quantidade de estoque inválida."
            )
            return

        try:
            price = float(
                str(data["price"]).replace(",", ".")
            )

            if price <= 0:
                raise ValueError

        except ValueError:
            QMessageBox.warning(
                self,
                "Erro",
                "Preço inválido."
            )
            return

    
        new_product = create_product({
            "name": data["name"].strip(),
            "barcode": data["barcode"] or "",
            "price": price,
            "stock": stock,
            "unit_of_measure": data["unit_of_measure"],
            "description": data["description"] or "Sem descrição"
        })

        if not new_product:
            return

        events.product_changed.emit()
        self._add_product_to_cart(new_product)

    def add_item_by_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return

        product = get_product_by_barcode(barcode)

        if not product:
            resposta = QMessageBox.question(
                self,
                "Produto não encontrado",
                "Esse produto ainda não está cadastrado.\n"
                "Deseja cadastrar agora e já vender?",
                QMessageBox.Yes | QMessageBox.No  # type: ignore
            )
            if resposta == QMessageBox.Yes:  # type: ignore
                self._quick_register_product(prefill_barcode=barcode)

            self.barcode_input.clear()
            return

        self._add_product_to_cart(product)
        self.barcode_input.clear()

    def _on_search_text_changed(self, text):
        if len(text.strip()) < 2:
            self._search_timer.stop()
            self.results_list.clear()
            return
        self._search_timer.start()

    def _run_name_search(self):
        self.search_by_name(self.search_input.text())

    def search_by_name(self, text):
        self.results_list.clear()
        if len(text) < 2:
            return

        results = search_products(text)

        for product in results:
            unit = product.get("unit_of_measure", "un")
            nome_padronizado = product['name'].strip().title()
            description = clean_description(product.get("description"))
            price_text = format_unit_price(product["price"], unit)
            label = f"{nome_padronizado} - {price_text}"
            if description:
                label = f"{label}\n{description}"
            item = QListWidgetItem(label)
            item.setToolTip(name_tooltip(nome_padronizado, description))
            item.setData(Qt.ItemDataRole.UserRole, product)  
            self.results_list.addItem(item)

        if not results:
            quick_add_item = QListWidgetItem(f'➕ Cadastrar "{text}" como novo produto')
            quick_add_item.setData(
                Qt.ItemDataRole.UserRole,  # type: ignore
                {"__quick_add__": True, "name": text}
            )
            self.results_list.addItem(quick_add_item)

    def add_product_from_search(self, item):
        product = item.data(Qt.ItemDataRole.UserRole)

        if not product:
            return

        if product.get("__quick_add__"):
            self.search_input.clear()
            self.results_list.clear()
            self._quick_register_product(prefill_name=product["name"])
            return

        self._add_product_to_cart(product)
        self.search_input.clear()
        self.results_list.clear()

    def finish_sale(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Aviso", "Nenhum item na venda")
            return

        items = []
        for product_id, data in self.cart.items():
            items.append({
                "product_id": product_id,
                "quantity": data["qty"]
            })
        payment_method = self.payment_combo.currentText()
        sold_at = self._get_selected_sale_datetime()
        sold_at_payload = sold_at.isoformat() if sold_at else None

        self.finish_button.setEnabled(False)
        self.finish_button.setText("Processando...")

        try:
            success = create_sale(items, payment_method, sold_at=sold_at_payload)
        finally:
            self.finish_button.setEnabled(True)
            self.finish_button.setText("Finalizar venda")

        if success:
            receipt_text = self.build_receipt_text(sale_datetime=sold_at)
            if self.print_checkbox.isChecked():
                print_receipt(receipt_text)

            if sold_at:
                success_msg = (
                    f"Venda registrada para {sold_at.strftime('%d/%m/%Y')}"
                )
            else:
                success_msg = "Venda registrada com sucesso"

            QMessageBox.information(self, "Sucesso", success_msg)
            events.sale_completed.emit()
            self.table.setRowCount(0)
            self.total = 0.0
            self.total_label.setText("Total: R$ 0,00")
            self.cart.clear()
            self.refresh_table()
        else:
            QMessageBox.critical(self, "Erro", "Erro ao registrar venda")
            return

        self.print_checkbox.setChecked(False)
        self.payment_combo.setCurrentIndex(0)
        self.backdate_checkbox.setChecked(False)
        self.sale_date_input.setDate(QDate.currentDate().addDays(-1))

    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        total = 0.0

        for product_id, data in self.cart.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            unit = data.get("unit", "un")

            name_item = QTableWidgetItem(
                name_with_description(
                    data["name"],
                    data.get("description"),
                )
            )
            name_item.setData(Qt.ItemDataRole.UserRole, product_id)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # type: ignore
            name_item.setToolTip(
                name_tooltip(data["name"], data.get("description"))
            )

            qty_text = format_quantity_value(data["qty"], unit)
            qty_item = QTableWidgetItem(qty_text)
            qty_item.setTextAlignment(Qt.AlignCenter)  # type: ignore
            qty_item.setFlags(
                Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable  # type: ignore
            )

            btn_plus = QPushButton('➕')
            btn_plus.setFixedSize(32, 32)
            btn_plus.setObjectName("qtyPlus")
            btn_plus.clicked.connect(lambda _, pid=product_id: self.change_qty(pid, 1))

            btn_minus = QPushButton('➖')
            btn_minus.setFixedSize(32, 32)
            btn_minus.setObjectName("qtyMinus")
            btn_minus.clicked.connect(lambda _, pid=product_id: self.change_qty(pid, -1))

            price_label = format_unit_price(data["price"], unit)
            price_item = QTableWidgetItem(price_label)
            price_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # type: ignore

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, qty_item)
            self.table.setCellWidget(row, 2, btn_plus)
            self.table.setCellWidget(row, 3, btn_minus)
            self.table.setItem(row, 4, price_item)

            total += data["qty"] * data["price"]

        self.total = total
        self.total_label.setText(f"Total: R$ {self.total:.2f}")
        self.table.resizeRowsToContents()
        self.table.blockSignals(False)

    def build_receipt_text(self, sale_datetime=None):
        me = get_me() or {}
        store = me.get("store", {})

        store_name = store.get("name", "LOJA")
        store_cnpj = store.get("cnpj", "")

        receipt_datetime = sale_datetime or datetime.now()

        lines = []
        lines.append("================================")
        lines.append(f"        LOJA {store_name.upper()}")
        if store_cnpj:
            lines.append(f"        CNPJ: {store_cnpj}")
        lines.append("         CUPOM NAO FISCAL")
        lines.append("================================")
        lines.append(f"Data: {receipt_datetime.strftime('%d/%m/%Y %H:%M')}")
        lines.append("Pagamento efetuado via " + self.payment_combo.currentText())
        lines.append("--------------------------------")

        for item in self.cart.values():
            unit = item.get("unit", "un")
            subtotal = item["qty"] * item["price"]
            lines.append(item["name"])
            if is_fractional_unit(unit):
                lines.append(
                    f'{format_quantity(item["qty"], unit)} x '
                    f'{item["price"]:.2f}/{unit_suffix(unit)} = {subtotal:.2f}'
                )
            else:
                lines.append(f'{int(item["qty"])} x {item["price"]:.2f} = {subtotal:.2f}')

        lines.append("--------------------------------")
        lines.append(f"TOTAL: R$ {self.total:.2f}")
        lines.append("================================")
        lines.append("Obrigado pela preferência!")
        lines.append("\n\n\n")

        return "\n".join(lines)

    def change_qty(self, product_id, delta):

        if product_id not in self.cart:
            return

        data = self.cart[product_id]

        new_qty = data["qty"] + delta

        stock = data.get("stock")
        unit = data.get("unit", "un")

        if stock is not None and new_qty > stock:

            QMessageBox.warning(
                self,
                "Estoque insuficiente",
                f"Disponível: {format_quantity(stock, unit)}"
            )

            return

        if new_qty <= 0:

            del self.cart[product_id]

        else:

            self.cart[product_id]["qty"] = new_qty

        self.refresh_table()