from asyncio import events
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox,
    QListWidget, QListWidgetItem,QCheckBox,QComboBox
)
from PySide6.QtCore import Qt
from services.sales import (
    get_product_by_barcode,
    create_sale,
    search_products
)
from PySide6.QtWidgets import QMessageBox
from utils.printer import print_receipt
from datetime import datetime
from events import events
from services.auth import get_me



class PDVView(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        # =========================
        # Código de barras
        # =========================
        layout.addWidget(QLabel("Código de barras"))

        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Digite ou escaneie o código de barras")
        self.barcode_input.returnPressed.connect(self.add_item_by_barcode)
        layout.addWidget(self.barcode_input)

        # =========================
        # Busca por nome
        # =========================
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar produto pelo nome")
        self.search_input.textChanged.connect(self.search_by_name)
        layout.addWidget(self.search_input)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.add_product_from_search)
        layout.addWidget(self.results_list)

        # =========================
        # Tabela do carrinho
        # =========================
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Produto", "Qtd", "+","-","Preço", ""])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.remove_button = QPushButton("Remover item selecionado")
        self.remove_button.clicked.connect(self.remove_selected_item)
        layout.addWidget(self.remove_button)

        # =========================
        # Total
        # =========================
        self.total_label = QLabel("Total: R$ 0,00")
        self.total_label.setAlignment(Qt.AlignRight) # type: ignore
        layout.addWidget(self.total_label)

        # =========================
        # Opção de impressão
        # =========================
        self.print_checkbox = QCheckBox("Imprimir recibo")
        self.print_checkbox.setChecked(True)  # padrão ligado
        layout.addWidget(self.print_checkbox)


        # =========================
        # Forma de pagamento
        # =========================
        layout.addWidget(QLabel("Forma de pagamento"))

        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["dinheiro", "cartão de crédito","cartão de débito", "pix"])
        layout.addWidget(self.payment_combo)


        # =========================
        # Finalizar venda
        # =========================
        self.finish_button = QPushButton("Finalizar venda")
        self.finish_button.clicked.connect(self.finish_sale)
        layout.addWidget(self.finish_button)

        self.setLayout(layout)
        self.cart = {}  # product_id -> {name, price, qty}

        self.table.itemChanged.connect(self.on_qty_changed) # type: ignore

        self.total = 0.0

    def on_qty_changed(self, item):
        if item.column() != 1:
            return

        row = item.row()
        name_item = self.table.item(row, 0)
        if not name_item:
            return

        product_id = name_item.data(Qt.ItemDataRole.UserRole)

        try:
            qty = int(item.text())
            
            stock = self.cart[product_id]["stock"]

            if qty > stock:
                QMessageBox.warning(
                    self,
                    "Estoque insuficiente",
                    f"Estoque disponível: {stock}"
                )
                self.refresh_table()
                return

            if qty <= 0:
                del self.cart[product_id]
            else:
                self.cart[product_id]["qty"] = qty

        except ValueError:
            return

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



    # =====================================================
    # ADICIONAR POR CÓDIGO DE BARRAS
    # =====================================================
    def add_item_by_barcode(self):
        barcode = self.barcode_input.text().strip()
        if not barcode:
            return

        product = get_product_by_barcode(barcode)

        if not product:
            QMessageBox.warning(self, "Erro", "Produto não encontrado")
            self.barcode_input.clear()
            return

        product_id = product["id"]
        current_qty = self.cart.get(product_id, {}).get("qty", 0)

        if current_qty + 1 > product["stock"]:
            QMessageBox.warning(
                self,
                "Estoque insuficiente",
                f'Estoque disponível: {product["stock"]}'
            )
            self.barcode_input.clear()
            return

        product_id = product["id"]
        current_qty = self.cart.get(product_id, {}).get("qty", 0)
        stock = product["stock"]

        if current_qty + 1 > stock:
            QMessageBox.warning(
                self,
                "Estoque insuficiente",
                f"Estoque disponível: {stock}"
            )
            self.barcode_input.clear()
            return

        if product_id in self.cart:
            self.cart[product_id]["qty"] += 1
        else:
            self.cart[product_id] = {
                "name": product["name"],
                "price": product["price"],
                "qty": 1,
                "stock": stock
            }

        self.refresh_table()
        self.barcode_input.clear()


    # =====================================================
    # BUSCA POR NOME
    # =====================================================
    def search_by_name(self, text):
        self.results_list.clear()
        if len(text) < 2:
            return

        for product in search_products(text):
            item = QListWidgetItem(
                f'{product["name"]} - R$ {product["price"]:.2f}'
            )
            item.setData(Qt.ItemDataRole.UserRole, product) # type: ignore
            self.results_list.addItem(item)

    def add_product_from_search(self, item):
        product = item.data(Qt.ItemDataRole.UserRole)

        if not product:
            return  # evita erro quando item não tem produto

        product_id = product["id"]
        current_qty = self.cart.get(product_id, {}).get("qty", 0)
        stock = product["stock"]

        if current_qty + 1 > stock:
            QMessageBox.warning(
                self,
                "Estoque insuficiente",
                f"Estoque disponível: {stock}"
            )
            return

        if product_id in self.cart:
            self.cart[product_id]["qty"] += 1
        else:
            self.cart[product_id] = {
                "name": product["name"],
                "price": product["price"],
                "qty": 1,
                "stock": stock
            }

        self.refresh_table()
        self.search_input.clear()
        self.results_list.clear()



    # =====================================================
    # FINALIZAR VENDA
    # =====================================================
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
        success = create_sale(items,payment_method)

        if success:
            receipt_text = self.build_receipt_text()
            if self.print_checkbox.isChecked():
                print_receipt(receipt_text)

            QMessageBox.information(self, "Sucesso", "Venda registrada com sucesso")
            events.sale_completed.emit()
            self.table.setRowCount(0)
            self.total = 0.0
            self.total_label.setText("Total: R$ 0,00")
            self.cart.clear()
            self.refresh_table()
        else:
            QMessageBox.critical(self, "Erro", "Erro ao registrar venda")
            return

        self.print_checkbox.setChecked(True)
        self.payment_combo.setCurrentIndex(0)



    def refresh_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        total = 0.0

        for product_id, data in self.cart.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QTableWidgetItem(data["name"])
            name_item.setData(Qt.ItemDataRole.UserRole, product_id)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled) # type: ignore

            qty_item = QTableWidgetItem(str(data["qty"]))
            qty_item.setTextAlignment(Qt.AlignCenter) # type: ignore
            qty_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled) # type: ignore

            # Botão +
            btn_plus = QPushButton('➕')
                                                 
            btn_plus.setFixedSize(32, 32)
            btn_plus.setObjectName("qtyPlus")
            btn_plus.clicked.connect(lambda _, pid=product_id: self.change_qty(pid, 1))

            # Botão -
            btn_minus = QPushButton('➖')
            btn_minus.setFixedSize(32, 32)
            btn_minus.setObjectName("qtyMinus")
            btn_minus.clicked.connect(lambda _, pid=product_id: self.change_qty(pid, -1))


            btn_plus.setObjectName("qtyPlus")
            btn_minus.setObjectName("qtyMinus")


            price_item = QTableWidgetItem(f'{data["price"]:.2f}')
            price_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled) # type: ignore

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, qty_item)
            self.table.setCellWidget(row, 2, btn_plus)
            self.table.setCellWidget(row, 3, btn_minus)
            self.table.setItem(row, 4, price_item)

            total += data["qty"] * data["price"]

        self.total = total
        self.total_label.setText(f"Total: R$ {self.total:.2f}")
        self.table.blockSignals(False)


    def build_receipt_text(self):
        me = get_me() or {}
        store = me.get("store", {})

        store_name = store.get("name", "LOJA")
        store_cnpj = store.get("cnpj", "")

        lines = []
        lines.append("================================")
        lines.append(f"        LOJA {store_name.upper()}")
        if store_cnpj:
            lines.append(f"        CNPJ: {store_cnpj}")
        lines.append("         CUPOM NAO FISCAL")
        lines.append("================================")
        lines.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        lines.append("Pagamento efetuado via " + self.payment_combo.currentText())
        lines.append("--------------------------------")

        for item in self.cart.values():
            subtotal = item["qty"] * item["price"]
            lines.append(item["name"])
            lines.append(f'{item["qty"]} x {item["price"]:.2f} = {subtotal:.2f}')

        lines.append("--------------------------------")
        lines.append(f"TOTAL: R$ {self.total:.2f}")
        lines.append("================================")
        lines.append("Obrigado pela preferência!")
        lines.append("\n\n\n")

        return "\n".join(lines)

    def change_qty(self, product_id, delta):
        if product_id not in self.cart:
            return

        new_qty = self.cart[product_id]["qty"] + delta
        stock = self.cart[product_id]["stock"]

        if new_qty > stock:
            QMessageBox.warning(self, "Estoque insuficiente", f"Disponível: {stock}")
            return

        if new_qty <= 0:
            del self.cart[product_id]
        else:
            self.cart[product_id]["qty"] = new_qty

        self.refresh_table()


            
    
