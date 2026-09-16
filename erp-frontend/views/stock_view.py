from PySide6.QtWidgets import (

    QWidget, QVBoxLayout, QLabel,

    QTableWidget, QTableWidgetItem,QPushButton,QHBoxLayout,QDialog,QFormLayout,QLineEdit,

    QDoubleSpinBox,

    QDialogButtonBox,QMessageBox,QTextEdit,QInputDialog,QCheckBox,QComboBox,
    QHeaderView, QSizePolicy, QStackedWidget

)

from PySide6.QtCore import Qt, QSize, QTimer

from services.products import (
    list_products,
    create_product,
    add_stock,
    update_product_barcode,
    update_product,
)
from views.product_photo_dialog import ProductPhotoDialog
from views.product_photo_preview_dialog import ProductPhotoPreviewDialog
from utils.product_images import (
    get_product_photo_icon,
    has_cached_photo_icon,
    invalidate_photo_cache,
    placeholder_photo_icon,
)
from events import events

from PySide6.QtGui import QColor

from utils.units import (

    UNIT_CHOICES,

    format_quantity,
    format_quantity_value,
    format_price_label,

    format_stock_add_prompt,
    format_stock_label,

    format_unit_price,

    is_fractional_unit,

    qty_step,
    unit_suffix,

)
from utils.product_display import (
    clean_description,
    name_tooltip,
)



COL_PHOTO = 0
COL_NAME = 1
COL_DESC = 2
COL_PRICE = 3
COL_QTY = 4
COL_UNIT = 5
COL_BARCODE = 6

PHOTO_ICON_SIZE = 48
STOCK_ROW_HEIGHT = 56


def is_placeholder_barcode(barcode: str | None) -> bool:
    if not barcode or not str(barcode).strip():
        return True
    return str(barcode).strip().upper().startswith("INT-")


def format_barcode_label(barcode: str | None) -> str:
    if is_placeholder_barcode(barcode):
        return "Sem código"
    return str(barcode).strip()


def barcode_tooltip(barcode: str | None) -> str:
    if not barcode or not str(barcode).strip():
        return (
            "Produto sem código de barras.\n"
            "Use 'Adicionar código de barras' quando tiver o código."
        )

    if str(barcode).strip().upper().startswith("INT-"):
        return (
            f"Código interno antigo: {barcode}\n"
            "Use 'Adicionar código de barras' para cadastrar o código real."
        )

    return str(barcode).strip()


def bind_growing_text_edit(text_edit: QTextEdit, min_h: int = 80, max_h: int = 220):
    text_edit.setMinimumHeight(min_h)
    text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def adjust():
        doc_h = int(text_edit.document().size().height())
        margins = text_edit.contentsMargins()
        height = doc_h + margins.top() + margins.bottom() + 16
        text_edit.setFixedHeight(max(min_h, min(max_h, height)))

    text_edit.textChanged.connect(adjust)
    QTimer.singleShot(0, adjust)



class StockView(QWidget):

    def __init__(self):

        super().__init__()
        self.products = []
        self._loaded = False
        self._photo_load_token = 0
        self._pending_photos = []
        events.sale_completed.connect(self._on_sale_completed)
        events.product_changed.connect(self._on_product_changed)

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

        self.btn_add_barcode = QPushButton("🏷️ Adicionar código de barras")
        self.btn_add_barcode.clicked.connect(self.open_add_barcode)
        layout.addWidget(self.btn_add_barcode)

        self.btn_edit_product = QPushButton("✏️ Editar produto")
        self.btn_edit_product.clicked.connect(self.open_edit_product)
        layout.addWidget(self.btn_edit_product)

        self.btn_add_photo = QPushButton("📷 Adicionar foto")
        self.btn_add_photo.clicked.connect(self.open_product_photo)
        layout.addWidget(self.btn_add_photo)



        



        title = QLabel("Estoque")

        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        layout.addWidget(title)




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





        self.table = QTableWidget(0, 7)

        self.table.setHorizontalHeaderLabels(

            ["Foto", "Produto", "Descrição", "Preço", "Quantidade", "Unidade", "Código de barras"]

        )
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setIconSize(QSize(PHOTO_ICON_SIZE, PHOTO_ICON_SIZE))
        self.table.setColumnWidth(COL_PHOTO, 64)
        self.table.setColumnWidth(COL_PRICE, 125)
        self.table.setColumnWidth(COL_QTY, 150)
        self.table.setColumnWidth(COL_UNIT, 90)
        self.table.setColumnWidth(COL_BARCODE, 180)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(COL_PHOTO, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_DESC, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_PRICE, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_QTY, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_UNIT, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_BARCODE, QHeaderView.Fixed)
        self.table.verticalHeader().setDefaultSectionSize(STOCK_ROW_HEIGHT)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)



        layout.addWidget(self.table)

        self.table.itemSelectionChanged.connect(
            self._update_action_buttons_state
        )
        self.table.cellClicked.connect(self._on_table_cell_clicked)

        self.setLayout(layout)
        self._update_action_buttons_state()





    def load_stock(self, extra_product=None):
        products = list_products()
        if products is None:
            products = list(self.products)
        if extra_product and extra_product.get("id"):
            extra_id = extra_product.get("id")
            if not any(p.get("id") == extra_id for p in products):
                products.append(extra_product)

        self.products = products
        self.populate_table(self.products)
        self._apply_search_filter()
        self._loaded = True

    def ensure_loaded(self):
        if not self._loaded:
            self.load_stock()

    def _is_current_page(self) -> bool:
        parent = self.parentWidget()
        if isinstance(parent, QStackedWidget):
            return parent.currentWidget() is self
        return self.isVisible()

    def _on_sale_completed(self):
        if self._is_current_page():
            self.load_stock()
        else:
            self._loaded = False

    def _on_product_changed(self):
        if self._is_current_page():
            self.load_stock()
        else:
            self._loaded = False

    def _clear_search_silently(self):
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

    def _scroll_to_product(self, product_id):
        if product_id is None:
            return
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_NAME)
            if item is None or item.data(Qt.UserRole) != product_id:
                continue
            self.table.selectRow(row)
            self.table.scrollToItem(item)
            break





                

    def open_add_product(self):

        dialog = AddProductDialog(self)



        if not dialog.exec():

            return



        data = dialog.get_data()



        if not data["name"]:
            QMessageBox.warning(self, "Erro", "Preencha o nome do produto")
            return

        if not data["without_barcode"] and not data["barcode"]:
            QMessageBox.warning(
                self,
                "Erro",
                "Informe o código de barras ou marque "
                "'Cadastrar sem código de barras por enquanto'."
            )
            return


        products = list_products() or []

        barcode = data["barcode"]
        if barcode and not is_placeholder_barcode(barcode):
            for p in products:
                if p.get("barcode") == barcode:
                    QMessageBox.warning(
                        self,
                        "Código duplicado",
                        "Já existe um produto com este código de barras."
                    )
                    return



        stock = (
            float(data["quantity"])
            if data["quantity"] is not None
            else None
        )

        product = create_product({

            "name": data["name"],

            "barcode": data["barcode"],

            "price": float(data["price"]),

            "stock": stock,

            "unit_of_measure": data["unit_of_measure"],

            "description": data["description"] or "Sem descrição"

        })



        if not product:
            return

        self._clear_search_silently()
        self.load_stock(extra_product=product)
        self._scroll_to_product(product.get("id"))
        self.table.viewport().update()
        QMessageBox.information(self, "Sucesso", "Produto cadastrado com sucesso")



    def open_add_stock(self):

        row = self.table.currentRow()

        if row < 0:

            QMessageBox.warning(self, "Atenção", "Selecione um produto")

            return



        item = self.table.item(row, COL_NAME)

        if not item:

            QMessageBox.critical(self, "Erro", "Produto inválido")

            return



        product_id = item.data(Qt.UserRole)  # type: ignore

        if product_id is None:

            QMessageBox.critical(self, "Erro", "ID do produto não encontrado")

            return



        product_name = item.text()

        unit = item.data(Qt.UserRole + 1) or "un"  # type: ignore



        if is_fractional_unit(unit):

            quantity, ok = QInputDialog.getDouble(

                self,

                "Entrada de estoque",

                format_stock_add_prompt(product_name, unit),

                0.1, 0.001, 99999.0, 3

            )

        else:

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

            self.load_stock()

        except Exception as e:

            QMessageBox.critical(self, "Erro", str(e))



    def _get_selected_product(self):
        row = self.table.currentRow()
        if row < 0:
            return None

        item = self.table.item(row, COL_NAME)
        if not item:
            return None

        product_id = item.data(Qt.UserRole)  # type: ignore
        if product_id is None:
            return None

        for product in self.products:
            if product.get("id") == product_id:
                return product

        return None



    def _update_action_buttons_state(self):
        product = self._get_selected_product()
        can_add_barcode = (
            product is not None
            and is_placeholder_barcode(product.get("barcode"))
        )
        self.btn_add_barcode.setEnabled(can_add_barcode)
        self.btn_edit_product.setEnabled(product is not None)
        self.btn_add_photo.setEnabled(product is not None)
        if product and product.get("image_path"):
            self.btn_add_photo.setText("📷 Trocar foto")
        else:
            self.btn_add_photo.setText("📷 Adicionar foto")


    def _on_table_cell_clicked(self, row, col):
        if col != COL_PHOTO:
            return
        self.table.selectRow(row)
        product = self._get_selected_product()
        if product and product.get("image_path"):
            self.open_product_photo_preview()
        else:
            self.open_product_photo()

    def open_product_photo_preview(self):
        product = self._get_selected_product()
        if not product:
            QMessageBox.warning(self, "Atenção", "Selecione um produto")
            return
        if not product.get("image_path"):
            self.open_product_photo()
            return

        dialog = ProductPhotoPreviewDialog(product, self)
        dialog.exec()
        if dialog.replace_requested:
            self.open_product_photo()
        elif dialog.photo_changed:
            invalidate_photo_cache(product.get("image_path"))
            self.load_stock()


    def open_product_photo(self):
        product = self._get_selected_product()
        if not product:
            QMessageBox.warning(self, "Atenção", "Selecione um produto")
            return

        dialog = ProductPhotoDialog(product, self)
        dialog.exec()
        invalidate_photo_cache(product.get("image_path"))
        self.load_stock()



    def open_add_barcode(self):
        product = self._get_selected_product()
        if not product:
            QMessageBox.warning(self, "Atenção", "Selecione um produto")
            return

        if not is_placeholder_barcode(product.get("barcode")):
            QMessageBox.information(
                self,
                "Atenção",
                "Este produto já possui código de barras cadastrado."
            )
            return

        dialog = AddBarcodeDialog(
            product.get("name", ""),
            self
        )

        if not dialog.exec():
            return

        barcode = dialog.get_barcode()
        if not barcode:
            QMessageBox.warning(
                self,
                "Erro",
                "Informe um código de barras válido."
            )
            return

        for other in self.products:
            if (
                other.get("id") != product.get("id")
                and other.get("barcode") == barcode
            ):
                QMessageBox.warning(
                    self,
                    "Código duplicado",
                    "Já existe um produto com este código de barras."
                )
                return

        updated = update_product_barcode(product["id"], barcode)
        if not updated:
            return

        QMessageBox.information(
            self,
            "Sucesso",
            "Código de barras cadastrado com sucesso."
        )
        self.load_stock()



    def open_edit_product(self):
        product = self._get_selected_product()
        if not product:
            QMessageBox.warning(self, "Atenção", "Selecione um produto")
            return

        dialog = EditProductDialog(product, self)
        if not dialog.exec():
            return

        data = dialog.get_data()
        if not data["name"]:
            QMessageBox.warning(self, "Erro", "Preencha o nome do produto")
            return

        updated = update_product(product["id"], data)
        if not updated:
            return

        QMessageBox.information(
            self,
            "Sucesso",
            "Produto atualizado com sucesso."
        )
        self.load_stock()


    def search_product(self):
        self._apply_search_filter()

    def _apply_search_filter(self):
        text = self.search_input.text().strip().lower()

        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_NAME)
            if item is None:
                self.table.setRowHidden(row, bool(text))
                continue

            product_id = item.data(Qt.UserRole)
            product = next(
                (p for p in self.products if p.get("id") == product_id),
                None,
            )
            if not text:
                self.table.setRowHidden(row, False)
                continue
            if not product:
                self.table.setRowHidden(row, True)
                continue

            match = (
                text in (product.get("name") or "").lower()
                or text in (product.get("barcode") or "").lower()
            )
            self.table.setRowHidden(row, not match)

    def clear_search(self):

        self.search_input.clear()

        self._apply_search_filter()



    def populate_table(self, products):

        products = sorted(
            products,
            key=lambda product: product.get("name", "").strip().casefold()
        )

        self._photo_load_token += 1
        token = self._photo_load_token
        pending = []

        self.table.setRowCount(0)
        self.table.setRowCount(len(products))

        for row, product in enumerate(products):

            unit = product.get("unit_of_measure", "un")
            image_path = product.get("image_path")

            item_photo = QTableWidgetItem()
            if has_cached_photo_icon(image_path, PHOTO_ICON_SIZE):
                item_photo.setIcon(
                    get_product_photo_icon(image_path, PHOTO_ICON_SIZE)
                )
            else:
                item_photo.setIcon(placeholder_photo_icon(PHOTO_ICON_SIZE))
                if image_path:
                    pending.append((row, image_path, product.get("id")))
            item_photo.setData(Qt.UserRole, product.get("id"))
            if image_path:
                item_photo.setToolTip("Clique para ver a foto em tamanho maior")
            else:
                item_photo.setToolTip("Clique para adicionar foto")
            item_photo.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, COL_PHOTO, item_photo)
            self.table.setRowHidden(row, False)

            nome_padronizado = product.get("name", "").strip().title()
            item_name = QTableWidgetItem(
               nome_padronizado
            )

            

            item_name.setData(
                Qt.UserRole,
                product.get("id")
            )  

            item_name.setData(
                Qt.UserRole + 1,
                unit
            )  

            description = clean_description(product.get("description"))
            item_name.setToolTip(
                name_tooltip(nome_padronizado, description)
            )

            self.table.setItem(row, COL_NAME, item_name)

            item_description = QTableWidgetItem(description)
            item_description.setToolTip(description)
            self.table.setItem(row, COL_DESC, item_description)


            price = product.get("price", 0)

            self.table.setItem(
                row,
                COL_PRICE,
                QTableWidgetItem(
                    format_unit_price(price, unit)
                )
            )

            stock_value = product.get("stock")

            if stock_value is None:
                stock = None
                stock_text = "Não informado"

            else:
                stock = float(stock_value)
                stock_text = format_quantity_value(stock, unit)

            
            critical = (
                stock is not None
                and stock <= 3
            )

            low = (
                stock is not None
                and stock <= 10
            )

            

            item_stock = QTableWidgetItem(stock_text)

            item_stock.setTextAlignment(
                Qt.AlignCenter
            )

            if critical:

                item_stock.setForeground(
                    QColor(255, 255, 255)
                )

                item_stock.setBackground(
                    QColor(139, 0, 0)
                )

                item_stock.setText(
                    f"{stock_text}  CRÍTICO"
                )

            elif low:

                item_stock.setForeground(
                    QColor(0, 0, 0)
                )

                item_stock.setBackground(
                    QColor(255, 255, 0)
                )

                item_stock.setText(
                    f"{stock_text}  BAIXO"
                )

            self.table.setItem(
                row,
                COL_QTY,
                item_stock
            )

            self.table.setItem(
                row,
                COL_UNIT,
                QTableWidgetItem(unit_suffix(unit))
            )

            barcode_label = format_barcode_label(product.get("barcode"))
            item_barcode = QTableWidgetItem(barcode_label)

            if is_placeholder_barcode(product.get("barcode")):
                item_barcode.setForeground(QColor(120, 120, 120))
                item_barcode.setToolTip(
                    barcode_tooltip(product.get("barcode"))
                )

            self.table.setItem(
                row,
                COL_BARCODE,
                item_barcode
            )

            for col in range(7):

                item = self.table.item(row, col)

                if item:

                    item.setFlags(
                        Qt.ItemIsSelectable
                        | Qt.ItemIsEnabled
                    )

        self._update_action_buttons_state()
        self.table.viewport().update()
        self._pending_photos = pending
        if pending:
            QTimer.singleShot(0, lambda: self._load_next_photo(token))

    def _load_next_photo(self, token):
        if token != self._photo_load_token:
            return
        if not self._pending_photos:
            return

        row, image_path, product_id = self._pending_photos.pop(0)
        item = self.table.item(row, COL_PHOTO)
        if item is not None and item.data(Qt.UserRole) == product_id:
            item.setIcon(get_product_photo_icon(image_path, PHOTO_ICON_SIZE))

        if self._pending_photos:
            QTimer.singleShot(0, lambda: self._load_next_photo(token))



class AddBarcodeDialog(QDialog):

    def __init__(self, product_name: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Adicionar código de barras")
        self.setMinimumWidth(360)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(
            QLabel(f"Produto: <b>{product_name}</b>")
        )
        layout.addWidget(
            QLabel(
                "Escaneie ou digite o código de barras "
                "para vincular ao produto."
            )
        )

        form = QFormLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Digite ou escaneie o código")
        form.addRow("Código de barras:", self.barcode_input)
        layout.addLayout(form)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel  # type: ignore
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_barcode(self) -> str:
        return self.barcode_input.text().strip()



class EditProductDialog(QDialog):

    def __init__(self, product: dict, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Editar produto")
        self.setMinimumWidth(360)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self.name_input.setText(product.get("name", "").strip())
        form.addRow("Nome:", self.name_input)

        self.unit_combo = QComboBox()
        for code, label in UNIT_CHOICES:
            self.unit_combo.addItem(label, code)
        current_unit = product.get("unit_of_measure") or "un"
        unit_index = self.unit_combo.findData(current_unit)
        if unit_index >= 0:
            self.unit_combo.setCurrentIndex(unit_index)
        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)
        form.addRow("Unidade de medida:", self.unit_combo)

        self.price_label = QLabel("Preço:")
        self.price_input = QDoubleSpinBox()
        self.price_input.setMaximum(999999)
        self.price_input.setDecimals(2)
        self.price_input.setPrefix("R$ ")
        self.price_input.setValue(float(product.get("price") or 0))
        form.addRow(self.price_label, self.price_input)

        self.description_input = QTextEdit()
        self.description_input.setPlainText(
            clean_description(product.get("description"))
        )
        bind_growing_text_edit(self.description_input)
        form.addRow("Descrição:", self.description_input)

        layout.addLayout(form)

        hint = QLabel(
            "Estoque e código de barras não são alterados aqui.\n"
            "Use as opções de entrada de estoque e código de barras."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel  # type: ignore
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self._on_unit_changed()

    def _on_unit_changed(self):
        unit = self.unit_combo.currentData()
        self.price_label.setText(format_price_label(unit))

    def get_data(self):
        description = self.description_input.toPlainText().strip()
        return {
            "name": self.name_input.text().strip().title(),
            "price": self.price_input.value(),
            "unit_of_measure": self.unit_combo.currentData(),
            "description": description or "Sem descrição",
        }


class AddProductDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)



        self.setWindowTitle("Cadastrar Produto")

        self.setMinimumWidth(360)



        layout = QVBoxLayout()

        layout.setContentsMargins(16, 16, 16, 16)

        layout.setSpacing(12)



        form = QFormLayout()

        form.setSpacing(10)



        self.name_input = QLineEdit()

        form.addRow("Nome:", self.name_input)



        self.unit_combo = QComboBox()

        for code, label in UNIT_CHOICES:
            self.unit_combo.addItem(label, code)

        self.unit_combo.currentIndexChanged.connect(self._on_unit_changed)

        form.addRow("Unidade de medida:", self.unit_combo)



        self.price_label = QLabel("Preço:")

        self.price_input = QDoubleSpinBox()

        self.price_input.setMaximum(999999)

        self.price_input.setDecimals(2)

        self.price_input.setPrefix("R$ ")

        form.addRow(self.price_label, self.price_input)



        self.qty_label = QLabel("Quantidade:")

        self.qty_input = QDoubleSpinBox()

        self.qty_input.setMaximum(99999)

        self.qty_input.setDecimals(0)

        self.qty_input.setSingleStep(1)

        form.addRow(self.qty_label, self.qty_input)

        self.define_stock_checkbox = QCheckBox(
            "Informar estoque inicial agora"
        )
        self.define_stock_checkbox.setChecked(False)
        self.define_stock_checkbox.toggled.connect(
            self._on_define_stock_toggled
        )
        form.addRow("", self.define_stock_checkbox)



        self.barcode_input = QLineEdit()

        self.barcode_input.setPlaceholderText("Escaneie ou digite o código")

        form.addRow("Código de barras:", self.barcode_input)



        self.no_barcode_checkbox = QCheckBox(
            "Cadastrar sem código de barras por enquanto"
        )

        self.no_barcode_checkbox.toggled.connect(self._on_no_barcode_toggled)

        form.addRow("", self.no_barcode_checkbox)



        self.description_input = QTextEdit()
        bind_growing_text_edit(self.description_input)
        form.addRow("Descrição:", self.description_input)



        layout.addLayout(form)



        button_box = QDialogButtonBox(

            QDialogButtonBox.Save | QDialogButtonBox.Cancel  # type: ignore

        )

        button_box.accepted.connect(self.accept)

        button_box.rejected.connect(self.reject)



        layout.addWidget(button_box)



        self.setLayout(layout)
        self._on_define_stock_toggled(False)



    def _on_define_stock_toggled(self, checked: bool):
        self.qty_input.setEnabled(checked)



    def _on_unit_changed(self):

        unit = self.unit_combo.currentData()

        self.price_label.setText(format_price_label(unit))

        self.qty_label.setText(format_stock_label(unit))



        if is_fractional_unit(unit):

            self.qty_input.setDecimals(3)

            self.qty_input.setSingleStep(qty_step(unit))

        else:

            self.qty_input.setDecimals(0)

            self.qty_input.setSingleStep(1)



    def _on_no_barcode_toggled(self, checked: bool):

        if checked:
            self.barcode_input.clear()
            self.barcode_input.setEnabled(False)
            self.barcode_input.setPlaceholderText(
                "Adicione depois em Estoque"
            )
        else:
            self.barcode_input.setEnabled(True)
            self.barcode_input.setPlaceholderText(
                "Escaneie ou digite o código"
            )



    def get_data(self):

        without_barcode = self.no_barcode_checkbox.isChecked()

        return {

            "name": self.name_input.text().strip().title(),

            "price": self.price_input.value(),

            "quantity": (
                self.qty_input.value()
                if self.define_stock_checkbox.isChecked()
                else None
            ),

            "unit_of_measure": self.unit_combo.currentData(),

            "barcode": (
                ""
                if without_barcode
                else self.barcode_input.text().strip()
            ),

            "without_barcode": without_barcode,

            "description": self.description_input.toPlainText()

        }


