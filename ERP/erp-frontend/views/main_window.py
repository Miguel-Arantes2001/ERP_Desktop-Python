from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget
)

from widgets.sidebar import Sidebar
from views.dashboard_view import DashboardView
from views.pdv_view import PDVView
from views.stock_view import StockView
from views.sales_view import SalesView
from views.stock_movements_view import StockMovementsView

import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ERP - Sistema")
        self.resize(1000, 600)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        self.sidebar.load_data()

        # Stack de páginas 
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Views
        self.dashboard = DashboardView()
        self.pdv = PDVView()
        self.stock = StockView()
        self.stock_movements = StockMovementsView()
        self.sales = SalesView()

        # Adiciona ao stack
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.pdv)
        self.stack.addWidget(self.stock)
        self.stack.addWidget(self.stock_movements)
        self.stack.addWidget(self.sales)

        # Navegação
        self.sidebar.dashboard_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.dashboard)
        )
        self.sidebar.pdv_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.pdv)
        )
        self.sidebar.stock_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.stock)
        )
        self.sidebar.stock_movements_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.stock_movements)
        )
        self.sidebar.sales_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.sales)
        )

        # Página inicial
        self.stack.setCurrentWidget(self.dashboard)

        self.stack.currentChanged.connect(self.on_page_changed)

    def on_page_changed(self, index):
        widget = self.stack.widget(index)

        load_fn = getattr(widget, "load_data", None)
        if callable(load_fn):
            load_fn()

    