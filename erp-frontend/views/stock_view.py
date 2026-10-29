from PySide6.QtWidgets import (

    QWidget, QVBoxLayout, QLabel,

    QTableWidget, QTableWidgetItem,QPushButton,QHBoxLayout,QDialog,QFormLayout,QLineEdit,

    QDoubleSpinBox,

    QDialogButtonBox,QMessageBox,QTextEdit,QInputDialog,QCheckBox,QComboBox,
    QHeaderView, QSizePolicy, QStackedWidget, QStyledItemDelegate, QStyle,
    QStyleOptionViewItem

)

from PySide6.QtCore import Qt, QSize, QTimer, QEvent

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

from PySide6.QtGui import QColor, QFont, QFontMetrics

from utils.categories import category_options
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
COL_PRICE = 2
COL_CATEGORY = 3
COL_DESC = 4
COL_QTY = 5
COL_UNIT = 6
COL_BARCODE = 7

PHOTO_ICON_SIZE = 48
PHOTO_COLUMN_WIDTH = 64
STOCK_ROW_HEIGHT = 56
NAME_ROW_HEIGHT_CAP = 120


class WrappedTextDelegate(QStyledItemDelegate):
    """Desenha o texto com quebra de linha.

    Com `is_expanded`, a quebra só acontece na linha aberta. Nas demais,
    o texto fica em uma linha, cortado com reticências.
    """

    def __init__(self, parent=None, bold=False, is_expanded=None):
        super().__init__(parent)
        self._bold = bold
        self._is_expanded = is_expanded

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        text = opt.text
        opt.text = ""

        widget = option.widget
        style = widget.style() if widget is not None else None
        if style is None:
            return

        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            opt,
            painter,
            widget,
        )
        if not text:
            return

        text_rect = style.subElementRect(
            QStyle.SubElement.SE_ItemViewItemText,
            opt,
            widget,
        )
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        color = (
            opt.palette.highlightedText().color()
            if selected
            else opt.palette.text().color()
        )
        font = QFont(opt.font)
        font.setBold(self._bold)

        painter.save()
        painter.setFont(font)
        painter.setPen(color)
        if self._is_expanded is None or self._is_expanded(index.row()):
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignTop
                | Qt.TextFlag.TextWordWrap,
                text,
            )
        else:
            single_line = " ".join(text.split())
            elided = QFontMetrics(font).elidedText(
                single_line,
                Qt.TextElideMode.ElideRight,
                text_rect.width(),
            )
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                elided,
            )
        painter.restore()


def is_placeholder_barcode(barcode: str | None) -> bool:
    if not barcode or not str(barcode).strip():
        return True
    return str(barcode).strip().upper().startswith("INT-")


def setup_category_combo(combo: QComboBox, current: str | None = None) -> None:
    """Preenche o combo e seleciona a categoria atual, se houver.

    O combo, por padrão, pede largura igual ao item mais longo. Nomes como
    "Combustíveis e lubrificantes" estouram o formulário e o texto corta.
    Aqui ele cresce junto com os outros campos, e a lista aberta mostra
    o nome completo.
    """
    combo.clear()
    combo.addItem("Selecione a categoria", None)
    for name in category_options(current):
        combo.addItem(name, name)

    combo.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Fixed,
    )
    combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    combo.setMinimumContentsLength(28)
    combo.setMinimumWidth(260)
    combo.setMaxVisibleItems(14)

    view = combo.view()
    view.setTextElideMode(Qt.TextElideMode.ElideNone)
    metrics = combo.fontMetrics()
    widest = 0
    for index in range(combo.count()):
        widest = max(widest, metrics.horizontalAdvance(combo.itemText(index)))
    view.setMinimumWidth(widest + 36)

    current_clean = (current or "").strip()
    if not current_clean:
        combo.setCurrentIndex(0)
        return

    index = combo.findData(current_clean)
    combo.setCurrentIndex(index if index >= 0 else 0)


def selected_category(combo: QComboBox) -> str | None:
    value = combo.currentData()
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
        self._name_expanded_row = None
        self._fitting_columns = False
        self._applying_row_heights = False
        events.sale_completed.connect(self._on_sale_completed)
        events.product_changed.connect(self._on_product_changed)

        buttons_layout = QHBoxLayout()



        btn_add = QPushButton("➕ Novo Produto")



        btn_add.setFixedWidth(200)

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





        self.table = QTableWidget(0, 8)

        self.table.setHorizontalHeaderLabels(

            ["Foto", "Produto", "Preço", "Categoria", "Descrição", "Quantidade", "Unidade", "Código de barras"]

        )
        name_header = self.table.horizontalHeaderItem(COL_NAME)
        if name_header:
            name_header.setToolTip("Clique no nome do produto para expandir")
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setIconSize(QSize(PHOTO_ICON_SIZE, PHOTO_ICON_SIZE))
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.table.setItemDelegateForColumn(
            COL_NAME,
            WrappedTextDelegate(self.table, bold=True),
        )
        self.table.setItemDelegateForColumn(
            COL_DESC,
            WrappedTextDelegate(
                self.table,
                bold=False,
                is_expanded=lambda row: row == self._name_expanded_row,
            ),
        )
        desc_header = self.table.horizontalHeaderItem(COL_DESC)
        if desc_header:
            desc_header.setToolTip("Clique na descrição para abrir o texto completo")


        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(PHOTO_COLUMN_WIDTH)
        for column in range(self.table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Fixed)
        category_header = self.table.horizontalHeaderItem(COL_CATEGORY)
        if category_header:
            category_header.setToolTip("Categoria")
        price_header = self.table.horizontalHeaderItem(COL_PRICE)
        if price_header:
            price_header.setToolTip("Preço")
        self.table.verticalHeader().setDefaultSectionSize(STOCK_ROW_HEIGHT)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table.viewport().installEventFilter(self)



        layout.addWidget(self.table)

        self.table.itemSelectionChanged.connect(
            self._update_action_buttons_state
        )
        self.table.cellClicked.connect(self._on_table_cell_clicked)

        self.setLayout(layout)
        self._update_action_buttons_state()

    def eventFilter(self, obj, event):
        if (
            obj is self.table.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            self._fit_stock_columns()
        return super().eventFilter(obj, event)

    def _fit_stock_columns(self):
        """Distribui a largura visível sem jogar coluna para fora da tela.

        O preço vem logo depois do nome e continua estreito. O código de
        barras reserva espaço para 13 dígitos e para o título da coluna.
        A descrição fica estreita; o texto todo aparece ao clicar nela.
        O que sobra vai para o nome do produto.
        """
        if self._fitting_columns:
            return

        viewport = self.table.viewport().width()
        if viewport < 100:
            return

        self._fitting_columns = True
        try:
            metrics = self.table.fontMetrics()
            header_metrics = self.table.horizontalHeader().fontMetrics()
            photo = PHOTO_COLUMN_WIDTH
            base = metrics.horizontalAdvance("R$ 999.99/kg") + 12
            price = base + 28
            unit = base + 16
            qty = base + 28
            barcode = max(
                metrics.horizontalAdvance("7891234567890"),
                header_metrics.horizontalAdvance("Código de barras"),
            ) + 28
            category = (
                metrics.horizontalAdvance("Combustíveis e lubrificantes") + 16
            )
            reserved = photo + price + unit + qty + barcode + category
            pool = viewport - reserved
            desc = max(140, int(pool * 0.32))
            name = pool - desc

            while name < 160 and desc > 120:
                desc -= 1
                name += 1
            while name < 140 and qty > base + 8:
                qty -= 1
                name += 1
            while name < 120 and category > base + 40:
                category -= 1
                name += 1

            widths = {
                COL_PHOTO: photo,
                COL_PRICE: price,
                COL_NAME: max(80, name),
                COL_CATEGORY: category,
                COL_DESC: desc,
                COL_QTY: qty,
                COL_UNIT: unit,
                COL_BARCODE: barcode,
            }
            widths[COL_NAME] += viewport - sum(widths.values())

            header = self.table.horizontalHeader()
            for column, width in widths.items():
                header.resizeSection(column, max(24, width))
        finally:
            self._fitting_columns = False

        self._apply_row_heights()





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


        products = list(self.products) 
        if not products:
            products =  list_products() or []

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

            "description": data["description"] or "Sem descrição",

            "category": data.get("category") or None,

        })



        if not product:
            return

        self._clear_search_silently()
        updated = list(self.products)
        updated.append(product)
        self.products = updated
        self.populate_table(self.products)
        self._apply_search_filter()
        self._loaded = True
        self._scroll_to_product(product.get("id"))
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
        if col == COL_NAME:
            self._toggle_name_expansion(row)
            return

        if col == COL_DESC:
            self._open_description(row)
            return

        if self._name_expanded_row is not None:
            self._collapse_name_column()

        if col != COL_PHOTO:
            return
        self.table.selectRow(row)
        product = self._get_selected_product()
        if product and product.get("image_path"):
            self.open_product_photo_preview()
        else:
            self.open_product_photo()

    def _open_description(self, row):
        name_item = self.table.item(row, COL_NAME)
        desc_item = self.table.item(row, COL_DESC)
        name = name_item.text() if name_item else ""
        description = desc_item.text() if desc_item else ""
        DescriptionDialog(name, description, self).exec()

    def _toggle_name_expansion(self, row):
        if self._name_expanded_row == row:
            self._collapse_name_column()
            return
        self._collapse_name_column()
        self._expand_name_column(row)

    def _expand_name_column(self, row):
        self._name_expanded_row = row
        self._apply_row_heights()

    def _wrapped_text_height(
        self,
        text: str,
        width: int,
        bold: bool,
        cap: int | None,
    ) -> int:
        clean = (text or "").strip()
        if not clean:
            return STOCK_ROW_HEIGHT
        font = QFont(self.table.font())
        font.setBold(bold)
        metrics = QFontMetrics(font)
        wrapped = metrics.boundingRect(
            0,
            0,
            max(width - 12, 40),
            0,
            Qt.TextFlag.TextWordWrap,
            clean,
        ).height() + 16
        height = max(STOCK_ROW_HEIGHT, wrapped)
        if cap is not None:
            height = min(height, cap)
        return height

    def _apply_row_heights(self):
        """Ajusta a altura: nome sempre legível, descrição só na linha aberta."""
        if self._applying_row_heights:
            return
        self._applying_row_heights = True
        try:
            for row in range(self.table.rowCount()):
                name_item = self.table.item(row, COL_NAME)
                expanded = row == self._name_expanded_row
                name_height = self._wrapped_text_height(
                    name_item.text() if name_item else "",
                    self.table.columnWidth(COL_NAME),
                    True,
                    None if expanded else NAME_ROW_HEIGHT_CAP,
                )
                desc_height = STOCK_ROW_HEIGHT
                if expanded:
                    desc_item = self.table.item(row, COL_DESC)
                    desc_height = self._wrapped_text_height(
                        desc_item.text() if desc_item else "",
                        self.table.columnWidth(COL_DESC),
                        False,
                        None,
                    )
                self.table.setRowHeight(
                    row,
                    max(STOCK_ROW_HEIGHT, name_height, desc_height),
                )
        finally:
            self._applying_row_heights = False
        self.table.viewport().update()

    def _collapse_name_column(self):
        self._name_expanded_row = None
        self._fit_stock_columns()

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
        self._collapse_name_column()

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
            price_text = format_unit_price(price, unit)
            item_price = QTableWidgetItem(price_text)
            item_price.setTextAlignment(
                Qt.AlignRight | Qt.AlignVCenter
            )
            item_price.setToolTip(price_text)
            self.table.setItem(row, COL_PRICE, item_price)

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

            category_label = (product.get("category") or "").strip()
            item_category = QTableWidgetItem(category_label)
            item_category.setToolTip(category_label)
            self.table.setItem(row, COL_CATEGORY, item_category)

            for col in range(8):

                item = self.table.item(row, col)

                if item:

                    item.setFlags(
                        Qt.ItemIsSelectable
                        | Qt.ItemIsEnabled
                    )

            

        self._update_action_buttons_state()
        self._apply_row_heights()
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



class DescriptionDialog(QDialog):
    """Mostra a descrição completa em uma área larga, com rolagem."""

    def __init__(self, product_name: str, description: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Descrição do produto")
        self.setMinimumSize(560, 360)
        self.resize(640, 420)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(product_name or "Produto")
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(description.strip() or "Sem descrição")
        text.setStyleSheet("font-size: 14px;")
        layout.addWidget(text)

        button_box = QDialogButtonBox(QDialogButtonBox.Close)  # type: ignore
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)


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
        self.setMinimumWidth(480)

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

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

        self.category_input = QComboBox()
        setup_category_combo(self.category_input, product.get("category"))
        form.addRow("Categoria:", self.category_input)

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
            "category": selected_category(self.category_input),
        }


class AddProductDialog(QDialog):

    def __init__(self, parent=None):

        super().__init__(parent)



        self.setWindowTitle("Cadastrar Produto")

        self.setMinimumWidth(480)



        layout = QVBoxLayout()

        layout.setContentsMargins(16, 16, 16, 16)

        layout.setSpacing(12)



        form = QFormLayout()

        form.setSpacing(10)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )



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

        self.category_input = QComboBox()
        setup_category_combo(self.category_input)
        form.addRow("Categoria:", self.category_input)



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

            "description": self.description_input.toPlainText(),

            "category": selected_category(self.category_input),

        }


