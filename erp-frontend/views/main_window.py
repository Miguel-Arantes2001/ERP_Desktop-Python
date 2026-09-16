
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QApplication
)

from widgets.sidebar import Sidebar
from views.dashboard_view import DashboardView
from views.pdv_view import PDVView
from views.quick_sale_view import QuickSaleView
from views.stock_view import StockView
from views.sales_view import SalesView
from views.stock_movements_view import StockMovementsView

import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ARMAZÉM RURAL")

        
        self.resize(1366, 800)

      
        self.setMinimumSize(1000, 650)

       
        self._center_on_screen()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        self.sidebar.load_data()

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.dashboard = DashboardView()
        self.pdv = PDVView()
        self.quick_sale = QuickSaleView()
        self.stock = StockView()
        self.stock_movements = StockMovementsView()
        self.sales = SalesView()

        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.pdv)
        self.stack.addWidget(self.quick_sale)
        self.stack.addWidget(self.stock)
        self.stack.addWidget(self.stock_movements)
        self.stack.addWidget(self.sales)

        self.sidebar.dashboard_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.dashboard)
        )
        self.sidebar.pdv_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.pdv)
        )
        self.sidebar.quick_sale_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.quick_sale)
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

        self.stack.currentChanged.connect(self.on_page_changed)
        self.stack.setCurrentWidget(self.dashboard)
        self.on_page_changed(self.stack.currentIndex())

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return

        screen_geometry = screen.availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

    def on_page_changed(self, index):
        widget = self.stack.widget(index)

        ensure = getattr(widget, "ensure_loaded", None)
        if callable(ensure):
            ensure()