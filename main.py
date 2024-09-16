import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QMenuBar
)
from PyQt5 import Qt, QtWidgets
import requests
import pandas as pd
import yfinance as yf
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.pyplot as plt

API_KEY = 'YOUR_API_KEY'  # Replace with your Alpha Vantage API key

def get_stock_overview(symbol):
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    return data

def get_current_price(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if not data.empty:
        return data['Close'][0]
    else:
        return None

def get_dividend_events(symbol):
    stock = yf.Ticker(symbol)
    dividends = stock.dividends
    if not dividends.empty:
        df = dividends.reset_index()
        df.columns = ['Date', 'Dividend']
        return df
    else:
        return pd.DataFrame()

class DividendTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Dividend Tracker')
        self.setGeometry(100, 100, 800, 600)
        self.portfolio = []
        self.initUI()

    def initUI(self):
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layouts
        self.main_layout = QVBoxLayout()
        self.form_layout = QHBoxLayout()
        self.table_layout = QVBoxLayout()

        # Form Widgets
        self.symbol_label = QLabel('Symbol:')
        self.symbol_input = QLineEdit()
        self.shares_label = QLabel('Shares:')
        self.shares_input = QLineEdit()
        self.cost_label = QLabel('Cost Basis per Share:')
        self.cost_input = QLineEdit()
        self.add_button = QPushButton('Add to Portfolio')
        self.add_button.clicked.connect(self.add_to_portfolio)

        self.form_layout.addWidget(self.symbol_label)
        self.form_layout.addWidget(self.symbol_input)
        self.form_layout.addWidget(self.shares_label)
        self.form_layout.addWidget(self.shares_input)
        self.form_layout.addWidget(self.cost_label)
        self.form_layout.addWidget(self.cost_input)
        self.form_layout.addWidget(self.add_button)

        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            'Symbol', 'Shares', 'Cost Basis', 'Current Price',
            'Market Value', 'Unrealized Gain/Loss', 'Dividend Per Share', 'Annual Dividend',
            'Dividend Yield (%)', 'Total Return (%)'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Context Menu for Table
        self.table.setContextMenuPolicy(Qt.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_menu)

        # Buttons
        self.calendar_button = QPushButton('Show Dividend Calendar')
        self.calendar_button.clicked.connect(self.show_dividend_calendar)
        self.projection_button = QPushButton('Show Income Projections')
        self.projection_button.clicked.connect(self.calculate_income_projections)
        self.report_button = QPushButton('Generate Income Report')
        self.report_button.clicked.connect(self.generate_income_report)
        self.allocation_button = QPushButton('Show Portfolio Allocation')
        self.allocation_button.clicked.connect(self.show_portfolio_allocation)

        # Add layouts to main layout
        self.table_layout.addWidget(self.table)
        self.table_layout.addWidget(self.calendar_button)
        self.table_layout.addWidget(self.projection_button)
        self.table_layout.addWidget(self.report_button)
        self.table_layout.addWidget(self.allocation_button)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.table_layout)

        # Set main layout
        self.central_widget.setLayout(self.main_layout)

        # Menu Bar for Import/Export
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')

        import_action = QtWidgets.QAction('Import Portfolio', self)
        import_action.triggered.connect(self.import_portfolio)
        file_menu.addAction(import_action)

        export_action = QtWidgets.QAction('Export Portfolio', self)
        export_action.triggered.connect(self.export_portfolio)
        file_menu.addAction(export_action)

    def add_to_portfolio(self):
        symbol = self.symbol_input.text().upper()
        try:
            shares = float(self.shares_input.text())
            cost_basis = float(self.cost_input.text())
        except ValueError:
            QMessageBox.warning(self, 'Input Error', 'Please enter valid numbers for shares and cost basis.')
            return

        if not symbol:
            QMessageBox.warning(self, 'Input Error', 'Please enter a stock symbol.')
            return

        # Fetch data to validate symbol
        overview = get_stock_overview(symbol)
        if 'Symbol' not in overview:
            QMessageBox.warning(self, 'Symbol Error', f'No data found for symbol: {symbol}')
            return

        # Add to portfolio
        self.portfolio.append({
            'symbol': symbol,
            'shares': shares,
            'cost_basis': cost_basis
        })

        # Clear input fields
        self.symbol_input.clear()
        self.shares_input.clear()
        self.cost_input.clear()

        # Update table
        self.update_table()

    def update_table(self):
        self.table.setRowCount(0)  # Clear existing data

        for stock in self.portfolio:
            symbol = stock['symbol']
            shares = stock['shares']
            cost_basis = stock['cost_basis']

            # Fetch current price and dividend data
            current_price = get_current_price(symbol)
            overview = get_stock_overview(symbol)
            if current_price is None or 'DividendPerShare' not in overview:
                continue

            market_value = current_price * shares
            unrealized_gain = market_value - (cost_basis * shares)
            dividend_per_share = float(overview['DividendPerShare']) if overview['DividendPerShare'] not in [None, 'None'] else 0.0
            annual_dividend = dividend_per_share * shares
            dividend_yield = (dividend_per_share / current_price) * 100 if current_price > 0 else 0.0
            total_return = ((market_value + annual_dividend) - (cost_basis * shares)) / (cost_basis * shares) * 100 if cost_basis > 0 else 0.0

            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(symbol))
            self.table.setItem(row_position, 1, QTableWidgetItem(f"{shares:.2f}"))
            self.table.setItem(row_position, 2, QTableWidgetItem(f"${cost_basis:.2f}"))
            self.table.setItem(row_position, 3, QTableWidgetItem(f"${current_price:.2f}"))
            self.table.setItem(row_position, 4, QTableWidgetItem(f"${market_value:.2f}"))
            self.table.setItem(row_position, 5, QTableWidgetItem(f"${unrealized_gain:.2f}"))
            self.table.setItem(row_position, 6, QTableWidgetItem(f"${dividend_per_share:.2f}"))
            self.table.setItem(row_position, 7, QTableWidgetItem(f"${annual_dividend:.2f}"))
            self.table.setItem(row_position, 8, QTableWidgetItem(f"{dividend_yield:.2f}%"))
            self.table.setItem(row_position, 9, QTableWidgetItem(f"{total_return:.2f}%"))

    def open_menu(self, position):
        menu = QtWidgets.QMenu()
        remove_action = menu.addAction("Remove Holding")
        action = menu.exec_(self.table.viewport().mapToGlobal(position))
        if action == remove_action:
            selected_row = self.table.currentRow()
            if selected_row >= 0:
                del self.portfolio[selected_row]
                self.update_table()

    def show_dividend_calendar(self):
        # Implementation as shown above
        # ...
        pass

    def calculate_income_projections(self):
        # Implementation as shown above
        # ...
        pass

    def generate_income_report(self):
        # Implementation as shown above
        # ...
        pass

    def show_portfolio_allocation(self):
        # Implementation as shown above
        # ...
        pass

    def import_portfolio(self):
        # Implementation as shown above
        # ...
        pass

    def export_portfolio(self):
        # Implementation as shown above
        # ...
        pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DividendTracker()
    window.show()
    sys.exit(app.exec_())
