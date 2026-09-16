from PySide6.QtWidgets import (    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QDateEdit, QFrame,
    QHeaderView, QScrollArea, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtCharts import (
    QChart, QChartView,
    QBarSet, QBarCategoryAxis, QValueAxis,
    QHorizontalBarSeries,
    QPieSeries
)
from PySide6.QtGui import QPainter, QColor, QFont, QBrush

from services.reports import (
    get_sales_summary,
    get_top_products,
    get_sales_by_payment,
)
from events import events
from utils.units import format_quantity


class DashboardView(QWidget):
    BAR_ROW_HEIGHT = 46
    BAR_CHART_VIEWPORT_HEIGHT = 360
    BAR_CHART_MAX_ITEMS = 15
    BAR_LABEL_MAX_CHARS = 36
    def __init__(self):
        super().__init__()
        self._loaded = False
        events.sale_completed.connect(self._on_sale_completed)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        outer_layout.addWidget(scroll_area)

        content = QWidget()
        scroll_area.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        filter_card = QFrame()
        filter_card.setObjectName("filterCard")

        filter_main_layout = QVBoxLayout(filter_card)
        filter_main_layout.setSpacing(10)

        filter_title = QLabel("Período de Análise")
        filter_title.setObjectName("filterCardTitle")
        filter_main_layout.addWidget(filter_title)

        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)

        self.btn_group = QButtonGroup(self)

        btn_today = QPushButton("Hoje")
        btn_yesterday = QPushButton("Ontem")
        btn_7days = QPushButton("Últimos 7 dias")
        btn_30days = QPushButton("Últimos 30 dias")
        btn_this_month = QPushButton("Este Mês")

        buttons = [btn_today, btn_yesterday, btn_7days, btn_30days, btn_this_month]

        for btn in buttons:
            btn.setCheckable(True)
            btn.setObjectName("quickFilterBtn")
            self.btn_group.addButton(btn)
            presets_layout.addWidget(btn)

        btn_today.setChecked(True)

        btn_today.clicked.connect(lambda: self._set_preset_date("today"))
        btn_yesterday.clicked.connect(lambda: self._set_preset_date("yesterday"))
        btn_7days.clicked.connect(lambda: self._set_preset_date("7days"))
        btn_30days.clicked.connect(lambda: self._set_preset_date("30days"))
        btn_this_month.clicked.connect(lambda: self._set_preset_date("this_month"))

        presets_layout.addStretch()
        filter_main_layout.addLayout(presets_layout)

        custom_date_layout = QHBoxLayout()
        custom_date_layout.setSpacing(10)

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())

        btn_filter = QPushButton("Filtrar Personalizado")
        btn_filter.setObjectName("applyCustomFilterBtn")
        btn_filter.clicked.connect(self._apply_custom_filter)

        custom_date_layout.addWidget(QLabel("De:"))
        custom_date_layout.addWidget(self.start_date)
        custom_date_layout.addWidget(QLabel("Até:"))
        custom_date_layout.addWidget(self.end_date)
        custom_date_layout.addWidget(btn_filter)
        custom_date_layout.addStretch()

        filter_main_layout.addLayout(custom_date_layout)
        layout.addWidget(filter_card)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)

        cards_layout.addWidget(
            self._create_kpi_card("Total Vendido", "R$ 0,00", "kpiValueTotal", "total_label")
        )
        cards_layout.addWidget(
            self._create_kpi_card("Qtd. de Vendas", "0", "kpiValueCount", "count_label")
        )
        cards_layout.addWidget(
            self._create_kpi_card("Ticket Médio", "R$ 0,00", "kpiValueTicket", "ticket_label")
        )
        cards_layout.addWidget(self._create_top_product_kpi_card())

        layout.addLayout(cards_layout)

        charts_title = QLabel("Visão Geral do Período")
        charts_title.setObjectName("title")
        layout.addWidget(charts_title)

        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(16)

        bar_chart_card = QFrame()
        bar_chart_card.setObjectName("chartCard")
        bar_chart_card_layout = QVBoxLayout(bar_chart_card)
        bar_chart_card_layout.setContentsMargins(12, 12, 12, 12)
        bar_chart_card_layout.setSpacing(8)

        bar_chart_header = QLabel("Top 15 produtos mais vendidos")
        bar_chart_header.setObjectName("chartCardTitle")
        bar_chart_card_layout.addWidget(bar_chart_header)

        self.bar_chart_hint = QLabel(
            "A quantidade aparece ao lado de cada produto. "
            "Nomes completos na tabela abaixo."
        )
        self.bar_chart_hint.setObjectName("chartCardHint")
        self.bar_chart_hint.setWordWrap(True)
        bar_chart_card_layout.addWidget(self.bar_chart_hint)

        self.bar_chart = QChart()
        self.bar_chart.legend().setVisible(False)
        self.bar_chart.setAnimationOptions(QChart.NoAnimation)
        self.bar_chart.setBackgroundVisible(False)
        self.bar_chart.setPlotAreaBackgroundVisible(True)
        self.bar_chart.setPlotAreaBackgroundBrush(QBrush(QColor("#FFFFFF")))

        self.bar_chart_view = QChartView(self.bar_chart)
        self.bar_chart_view.setRenderHint(QPainter.Antialiasing)
        self.bar_chart_view.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed
        )

        self.bar_chart_scroll = QScrollArea()
        self.bar_chart_scroll.setObjectName("barChartScroll")
        self.bar_chart_scroll.setWidgetResizable(True)
        self.bar_chart_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.bar_chart_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.bar_chart_scroll.setMinimumHeight(self.BAR_CHART_VIEWPORT_HEIGHT)
        self.bar_chart_scroll.setMaximumHeight(self.BAR_CHART_VIEWPORT_HEIGHT)

        self.bar_chart_inner = QWidget()
        self.bar_chart_inner_layout = QVBoxLayout(self.bar_chart_inner)
        self.bar_chart_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.bar_chart_inner_layout.addWidget(self.bar_chart_view)
        self.bar_chart_scroll.setWidget(self.bar_chart_inner)
        bar_chart_card_layout.addWidget(self.bar_chart_scroll)

        charts_layout.addWidget(bar_chart_card, stretch=3)

        pie_chart_card = QFrame()
        pie_chart_card.setObjectName("chartCard")
        pie_chart_card_layout = QVBoxLayout(pie_chart_card)
        pie_chart_card_layout.setContentsMargins(12, 12, 12, 12)
        pie_chart_card_layout.setSpacing(8)

        pie_chart_header = QLabel("Vendas por forma de pagamento")
        pie_chart_header.setObjectName("chartCardTitle")
        pie_chart_card_layout.addWidget(pie_chart_header)

        self.pie_chart = QChart()
        self.pie_chart.setAnimationOptions(QChart.NoAnimation)
        self.pie_chart.legend().setVisible(True)
        self.pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.pie_chart.setBackgroundVisible(False)

        self.pie_chart_view = QChartView(self.pie_chart)
        self.pie_chart_view.setRenderHint(QPainter.Antialiasing)
        self.pie_chart_view.setMinimumHeight(self.BAR_CHART_VIEWPORT_HEIGHT)
        pie_chart_card_layout.addWidget(self.pie_chart_view)

        charts_layout.addWidget(pie_chart_card, stretch=2)

        layout.addLayout(charts_layout)

        table_title = QLabel("Detalhamento — Produtos Mais Vendidos")
        table_title.setObjectName("title")
        layout.addWidget(table_title)

        self.products_table = QTableWidget(0, 2)
        self.products_table.setHorizontalHeaderLabels(["Produto", "Quantidade Vendida"])

        header = self.products_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        self.products_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.products_table.setMinimumHeight(220)

        layout.addWidget(self.products_table)

    def _create_kpi_card(self, title: str, default_val: str, value_object_name: str, attr_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpiCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(6)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("kpiCardTitle")

        lbl_val = QLabel(default_val)
        lbl_val.setObjectName(value_object_name)

        setattr(self, attr_name, lbl_val)

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(lbl_val)
        card_layout.addStretch()
        return card

    def _create_top_product_kpi_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("kpiCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(6)

        lbl_title = QLabel("Produto que mais faturou")
        lbl_title.setObjectName("kpiCardTitle")

        self.top_product_label = QLabel("—")
        self.top_product_label.setObjectName("kpiValueProduct")
        self.top_product_label.setWordWrap(True)

        self.top_product_hint = QLabel("Nenhuma venda no período")
        self.top_product_hint.setObjectName("kpiValueProductHint")
        self.top_product_hint.setWordWrap(True)

        card_layout.addWidget(lbl_title)
        card_layout.addWidget(self.top_product_label)
        card_layout.addWidget(self.top_product_hint)
        card_layout.addStretch()
        return card

    @staticmethod
    def _format_brl(value: float) -> str:
        return (
            f"R$ {value:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    def _set_preset_date(self, preset_type: str):
        today = QDate.currentDate()

        if preset_type == "today":
            self.start_date.setDate(today)
            self.end_date.setDate(today)
        elif preset_type == "yesterday":
            yesterday = today.addDays(-1)
            self.start_date.setDate(yesterday)
            self.end_date.setDate(yesterday)
        elif preset_type == "7days":
            self.start_date.setDate(today.addDays(-7))
            self.end_date.setDate(today)
        elif preset_type == "30days":
            self.start_date.setDate(today.addDays(-30))
            self.end_date.setDate(today)
        elif preset_type == "this_month":
            first_day = QDate(today.year(), today.month(), 1)
            self.start_date.setDate(first_day)
            self.end_date.setDate(today)

        self.load_data()

    def _apply_custom_filter(self):
        self.btn_group.setExclusive(False)
        for btn in self.btn_group.buttons():
            btn.setChecked(False)
        self.btn_group.setExclusive(True)

        self.load_data()

    def load_data(self):
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")

        summary = get_sales_summary(start, end)

        total = summary.get("total_sales", 0)
        count = summary.get("sale_count", 0)
        avg_ticket = summary.get("average_ticket", 0)

        self.total_label.setText(self._format_brl(float(total or 0)))
        self.count_label.setText(str(count))
        self.ticket_label.setText(self._format_brl(float(avg_ticket or 0)))
        self._fill_top_product_card(summary.get("top_product"), count)

        products = get_top_products()
        self._fill_products_table(products)
        self._update_bar_chart(products)

        payments = get_sales_by_payment()
        self._update_pie_chart(payments)
        self._loaded = True

    def _fill_top_product_card(self, top_product, sale_count):
        if not top_product:
            self.top_product_label.setText("—")
            self.top_product_label.setToolTip("")
            if sale_count:
                self.top_product_hint.setText(
                    "Nenhum produto cadastrado no período"
                )
            else:
                self.top_product_hint.setText("Nenhuma venda no período")
            return

        name = (top_product.get("name") or "").strip() or "—"
        unit = top_product.get("unit_of_measure") or "un"
        qty_text = format_quantity(float(top_product.get("quantity_sold") or 0), unit)
        price_text = self._format_brl(float(top_product.get("unit_price") or 0))
        revenue_text = self._format_brl(float(top_product.get("revenue") or 0))

        self.top_product_label.setText(name)
        self.top_product_label.setToolTip(name)
        self.top_product_hint.setText(
            f"{qty_text} × {price_text} = {revenue_text}"
        )

    def _fill_products_table(self, products):
        self.products_table.setRowCount(0)
        for item in products:
            row = self.products_table.rowCount()
            self.products_table.insertRow(row)
            self.products_table.setItem(row, 0, QTableWidgetItem(item["product"]))
            unit = item.get("unit_of_measure", "un")
            qty_text = format_quantity(float(item["quantity_sold"]), unit)
            self.products_table.setItem(row, 1, QTableWidgetItem(qty_text))

    def _update_bar_chart(self, products):
        self.bar_chart.removeAllSeries()
        for axis in self.bar_chart.axes():
            self.bar_chart.removeAxis(axis)

        items = products[: self.BAR_CHART_MAX_ITEMS]
        extra_count = max(0, len(products) - len(items))

        if not items:
            self.bar_chart_hint.setText("Nenhuma venda registrada ainda.")
            self.bar_chart.setTitle("Nenhuma venda registrada ainda")
            self.bar_chart_inner.setMinimumHeight(220)
            self.bar_chart_view.setMinimumHeight(220)
            self.bar_chart_view.setMaximumHeight(220)
            return

        if extra_count:
            self.bar_chart_hint.setText(
                f"Mostrando os {self.BAR_CHART_MAX_ITEMS} mais vendidos. "
                f"Outros {extra_count} estão na tabela abaixo."
            )
        else:
            self.bar_chart_hint.setText(
                "A quantidade aparece ao lado de cada produto. "
                "Nomes completos na tabela abaixo."
            )

        self.bar_chart.setTitle("")

        display_items = list(reversed(items))

        bar_set = QBarSet("Quantidade vendida")
        bar_set.setColor(QColor("#2563EB"))
        categories = []

        for item in display_items:
            bar_set.append(float(item["quantity_sold"]))
            categories.append(self._bar_category_label(item))

        series = QHorizontalBarSeries()
        series.append(bar_set)
        series.setBarWidth(0.62)
        series.setLabelsVisible(False)
        self.bar_chart.addSeries(series)

        axis_y = QBarCategoryAxis()
        axis_y.append(categories)
        axis_y.setLabelsFont(QFont("Segoe UI", 9))
        self.bar_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        max_qty = max(
            (float(item["quantity_sold"]) for item in display_items),
            default=0,
        )
        axis_x = QValueAxis()
        axis_x.setLabelFormat("%.0f" if max_qty >= 1 else "%.1f")
        axis_x.setRange(0, max(max_qty * 1.15, 1))
        axis_x.setLabelsFont(QFont("Segoe UI", 9))
        axis_x.setGridLineVisible(True)
        self.bar_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignTop)
        series.attachAxis(axis_x)

        chart_height = max(
            220,
            len(display_items) * self.BAR_ROW_HEIGHT + 56,
        )
        self.bar_chart_inner.setMinimumHeight(chart_height)
        self.bar_chart_view.setMinimumHeight(chart_height)
        self.bar_chart_view.setMaximumHeight(chart_height)

        margins = self.bar_chart.margins()
        margins.setLeft(8)
        margins.setRight(16)
        margins.setTop(4)
        margins.setBottom(8)
        self.bar_chart.setMargins(margins)

    def _bar_category_label(self, item: dict) -> str:
        name = self._truncate_chart_label(item["product"], max_chars=22)
        unit = item.get("unit_of_measure", "un")
        qty_text = format_quantity(float(item["quantity_sold"]), unit)
        return f"{name}  {qty_text}"

    @staticmethod
    def _truncate_chart_label(name: str, max_chars: int | None = None) -> str:
        limit = max_chars or DashboardView.BAR_LABEL_MAX_CHARS
        cleaned = " ".join(str(name).split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"

    def _update_pie_chart(self, payments):
        self.pie_chart.removeAllSeries()

        series = QPieSeries()
        for item in payments:
            label = item["payment_method"]
            value = item["total"] or 0
            if value <= 0:
                continue
            series.append(label, value)

        total = sum(pie_slice.value() for pie_slice in series.slices()) or 1
        for pie_slice in series.slices():
            pct = (pie_slice.value() / total) * 100
            pie_slice.setLabel(f"{pie_slice.label()} ({pct:.0f}%)")
            pie_slice.setLabelVisible(True)

        self.pie_chart.addSeries(series)

    def ensure_loaded(self):
        if not self._loaded:
            self.load_data()

    def _on_sale_completed(self):
        if self._loaded:
            self.load_data()