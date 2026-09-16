from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QDialogButtonBox
)
from utils.units import (
    format_unit_price,
    format_quantity,
    format_quantity_dialog_title,
    format_quantity_input_label,
    qty_step,
)


class FractionalQuantityDialog(QDialog):
    def __init__(self, product: dict, parent=None):
        super().__init__(parent)
        self._unit = product.get("unit_of_measure") or "un"
        self.setWindowTitle(format_quantity_dialog_title(self._unit))
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        name = product.get("name", "")
        self._price = product.get("price", 0)
        stock_value = product.get("stock")

        if stock_value is None:
            self._stock = None
        else:
            self._stock = float(stock_value)

        name_label = QLabel(f"<b>{name}</b>")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        description = (product.get("description") or "").strip()
        if description and description.casefold() != "sem descrição":
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        layout.addWidget(QLabel(format_unit_price(self._price, self._unit)))
        if self._stock is None:
            stock_text = "Não informado"
        else:
            stock_text = format_quantity(self._stock, self._unit)

        layout.addWidget(
            QLabel(f"Estoque disponível: {stock_text}")
        )

        form = QFormLayout()
        self.qty_input = QDoubleSpinBox()
        self.qty_input.setDecimals(3)
        self.qty_input.setMinimum(0.001)
        if self._stock is None:
            self.qty_input.setMaximum(9999.0)
        else:
            self.qty_input.setMaximum(max(self._stock, 0.001))

        self.qty_input.setSingleStep(qty_step(self._unit))
        form.addRow(format_quantity_input_label(self._unit), self.qty_input)
        layout.addLayout(form)

        self.subtotal_label = QLabel()
        layout.addWidget(self.subtotal_label)

        self.qty_input.valueChanged.connect(self._update_subtotal)
        if self._stock is None:
            self.qty_input.setValue(0.1)

        elif self._stock > 0:
            self.qty_input.setValue(min(0.1, self._stock))

        else:
            self.qty_input.setValue(0.1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel  # type: ignore
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_subtotal(self):
        quantity = self.qty_input.value()
        subtotal = quantity * self._price
        self.subtotal_label.setText(f"Subtotal: R$ {subtotal:.2f}")

    def get_quantity(self) -> float:
        return self.qty_input.value()

    def accept(self):
        quantity = self.qty_input.value()

        if quantity <= 0:
            return

        if self._stock is not None and quantity > self._stock:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self,
                "Estoque insuficiente",
                f"Disponível: {format_quantity(self._stock, self._unit)}",
            )

            return

        super().accept()
