from PySide6.QtCore import QObject, Signal

class AppEvents(QObject):
    sale_completed = Signal()
    product_changed = Signal()

events = AppEvents()
