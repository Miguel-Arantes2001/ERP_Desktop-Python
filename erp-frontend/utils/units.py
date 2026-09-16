FRACTIONAL_UNITS = frozenset({"kg", "m"})

UNIT_CHOICES = (
    ("un", "Unidade (un)"),
    ("kg", "Quilo (kg)"),
    ("m", "Metro (m)"),
)

_SUFFIX = {
    "un": "un",
    "kg": "kg",
    "m": "m",
}

_PRICE_LABEL = {
    "un": "Preço:",
    "kg": "Preço por kg:",
    "m": "Preço por metro:",
}

_STOCK_LABEL = {
    "un": "Quantidade:",
    "kg": "Estoque (kg):",
    "m": "Estoque (m):",
}

_INPUT_LABEL = {
    "un": "Quantidade:",
    "kg": "Peso (kg):",
    "m": "Metros (m):",
}

_DIALOG_TITLE = {
    "un": "Informar quantidade",
    "kg": "Informar peso",
    "m": "Informar metros",
}


def unit_suffix(unit: str) -> str:
    return _SUFFIX.get(unit, unit or "un")


def is_fractional_unit(unit: str) -> bool:
    return unit in FRACTIONAL_UNITS


def qty_step(unit: str) -> float:
    return 0.1 if is_fractional_unit(unit) else 1.0


def format_decimal_br(value: float, max_decimals: int = 3) -> str:
    text = f"{value:.{max_decimals}f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def format_quantity(qty: float, unit: str = "un") -> str:
    suffix = unit_suffix(unit)
    if is_fractional_unit(unit):
        return f"{format_decimal_br(qty, 3)} {suffix}"
    if qty == int(qty):
        return f"{int(qty)} {suffix}"
    return f"{format_decimal_br(qty, 2)} {suffix}"


def format_quantity_value(qty: float, unit: str = "un") -> str:
    if is_fractional_unit(unit):
        return format_decimal_br(qty, 3)
    if qty == int(qty):
        return str(int(qty))
    return format_decimal_br(qty, 2)


def format_price_label(unit: str) -> str:
    return _PRICE_LABEL.get(unit, "Preço:")


def format_stock_label(unit: str) -> str:
    return _STOCK_LABEL.get(unit, "Quantidade:")


def format_quantity_input_label(unit: str) -> str:
    return _INPUT_LABEL.get(unit, "Quantidade:")


def format_quantity_dialog_title(unit: str) -> str:
    return _DIALOG_TITLE.get(unit, "Informar quantidade")


def format_unit_price(price: float, unit: str) -> str:
    if is_fractional_unit(unit):
        return f"R$ {price:.2f}/{unit_suffix(unit)}"
    return f"R$ {price:.2f}"


def format_stock_add_prompt(product_name: str, unit: str) -> str:
    if unit == "kg":
        return f"Peso a adicionar (kg) para {product_name}:"
    if unit == "m":
        return f"Metros a adicionar para {product_name}:"
    return f"Quantidade a adicionar para {product_name}:"
