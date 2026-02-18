from itertools import product
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,QPushButton,QHBoxLayout,QDialog,QFormLayout,QLineEdit,
    QSpinBox,
    QDoubleSpinBox
    ,QDialogButtonBox,QMessageBox,QTextEdit,QInputDialog
)
from PySide6.QtCore import Qt
from services.products import list_products,create_product,add_stock
from PySide6.QtGui import QColor

class StockView(QWidget):
    def __init__(self):
        super().__init__()
        buttons_layout = QHBoxLayout()

        btn_add = QPushButton("➕ Novo Produto")

        btn_add.setFixedWidth(150)
        btn_add.clicked.connect(self.open_add_product)

        buttons_layout.addWidget(btn_add)
        buttons_layout.addStretch()
        layout = QVBoxLayout()

        layout.addLayout(buttons_layout)
    

        btn_add_stock = QPushButton("➕ Entrada de estoque")

    
        btn_add_stock.clicked.connect(self.open_add_stock)
        layout.addWidget(btn_add_stock)

        

        title = QLabel("Estoque")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)


        # 🔍 BUSCA DE PRODUTO
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nome ou código de barras...")

        btn_search = QPushButton("🔍 Pesquisar")
        btn_search.clicked.connect(self.search_product)

        btn_clear = QPushButton("✖ Limpar")
        btn_clear.clicked.connect(self.clear_search)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(btn_search)
        search_layout.addWidget(btn_clear)

        layout.addLayout(search_layout)

        self.search_input.textChanged.connect(self.search_product)


        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Produto", "Preço", "Quantidade", "Código de barras"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)
        self.setLayout(layout)


    def load_stock(self):
        self.products = list_products() or []
        self.populate_table(self.products)


                
    def open_add_product(self):
        dialog = AddProductDialog(self)

        if not dialog.exec():
            return

        data = dialog.get_data()

        if not data["name"] or not data["barcode"]:
            QMessageBox.warning(self, "Erro", "Preencha nome e código de barras")
            return

        # 🔒 valida código de barras duplicado
        products = list_products() or []
        for p in products:
            if p.get("barcode") == data["barcode"]:
                QMessageBox.warning(
                    self,
                    "Código duplicado",
                    "Já existe um produto com este código de barras."
                )
                return

        product = create_product({
            "name": data["name"],
            "barcode": data["barcode"],
            "price": float(data["price"]),
            "stock": int(data["quantity"]),
            "description": data["description"] or "Sem descrição"
        })

        if not product:
            return
        
        QMessageBox.information(self, "Sucesso", "Produto cadastrado com sucesso")

        self.load_stock()
        self.table.viewport().update()

    def showEvent(self, event):
        self.load_stock()
        super().showEvent(event)


    def open_add_stock(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Atenção", "Selecione um produto")
            return

        item = self.table.item(row, 0)
        if not item:
            QMessageBox.critical(self, "Erro", "Produto inválido")
            return

        product_id = item.data(Qt.UserRole)  # type: ignore
        if product_id is None:
            QMessageBox.critical(self, "Erro", "ID do produto não encontrado")
            return

        product_name = item.text()

        
        quantity, ok = QInputDialog.getInt(
            self,
            "Entrada de estoque",
            f"Quantidade a adicionar para {product_name}:",
            1, 1
        )

        if not ok:
            return

        reason, ok = QInputDialog.getText(
            self,
            "Motivo da entrada",
            "Motivo (opcional):"
        )

        try:
            add_stock(product_id, quantity, reason)
            QMessageBox.information(self, "Sucesso", "Estoque atualizado com sucesso")
            self.load_stock()  # ✅ método correto
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))


    def search_product(self):
        text = self.search_input.text().strip().lower()

        if not text:
            self.populate_table(self.products)
            return

        filtered = [
            p for p in self.products
            if text in p["name"].lower() or text in p["barcode"].lower()
        ]

        self.populate_table(filtered)
    
    def clear_search(self):
        self.search_input.clear()
        self.populate_table(self.products)


    def populate_table(self, products):
        self.table.setRowCount(0)

        for product in products:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ✅ ITEM COM ID
            item_name = QTableWidgetItem(product.get("name", ""))
            item_name.setData(Qt.UserRole, product.get("id")) # type: ignore

            description = product.get("description", "")
            if description:
                item_name.setToolTip(description)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, QTableWidgetItem(f'{product.get("price", 0):.2f}'))
            
            stock = product.get("stock", 0)

            item_stock = QTableWidgetItem(str(stock))
            item_stock.setTextAlignment(Qt.AlignCenter) # type: ignore

            if stock <= 3:
                item_stock.setForeground(QColor(255, 255, 255)) # branco
                item_stock.setBackground(QColor(139, 0, 0)) # darkRed
                item_stock.setText(f"{stock}  CRÍTICO")

            elif stock <= 10:
                item_stock.setForeground(QColor(0, 0, 0)) # black
                item_stock.setBackground(QColor(255, 255, 0)) # yellow
                item_stock.setText(f"{stock}  BAIXO")

            self.table.setItem(row, 2, item_stock)

            self.table.setItem(row, 3, QTableWidgetItem(product.get("barcode", "")))

            for col in range(4):
                self.table.item(row, col).setFlags( # type: ignore
                    Qt.ItemIsSelectable | Qt.ItemIsEnabled # type: ignore
                )






class AddProductDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Cadastrar Produto")
        self.setFixedSize(300, 250)

        layout = QVBoxLayout()

        form = QFormLayout()

        self.name_input = QLineEdit()
        form.addRow("Nome:", self.name_input)

        self.price_input = QDoubleSpinBox()
        self.price_input.setMaximum(999999)
        self.price_input.setDecimals(2)
        self.price_input.setPrefix("R$ ")
        form.addRow("Preço:", self.price_input)

        self.qty_input = QSpinBox()
        self.qty_input.setMaximum(99999)
        form.addRow("Quantidade:", self.qty_input)

        self.barcode_input = QLineEdit()
        form.addRow("Código de barras:", self.barcode_input)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(60)
        form.addRow("Descrição:", self.description_input)


        layout.addLayout(form)

        # botões
        buttons = QHBoxLayout()

        btn_save = QPushButton("Salvar")
        btn_cancel = QPushButton("Cancelar")

        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)

        buttons.addStretch()
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)

        layout.addLayout(buttons)

        self.setLayout(layout)

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "price": self.price_input.value(),
            "quantity": self.qty_input.value(),
            "barcode": self.barcode_input.text(),
            "description": self.description_input.toPlainText()
    }

