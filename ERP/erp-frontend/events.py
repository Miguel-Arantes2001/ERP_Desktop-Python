from PySide6.QtCore import QObject, Signal

class AppEvents(QObject):
    sale_completed = Signal()

events = AppEvents()
