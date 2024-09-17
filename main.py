import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QMenuBar, QFileDialog, QStyleOptionHeader, QStyle, QAction
)
from PyQt5.QtCore import QRect, QRectF, Qt
from PyQt5.QtGui import QTextDocument
from PyQt5.QtWidgets import QHeaderView, QStyleOptionHeader, QStyle
from PyQt5.QtGui import QTextDocument
from PyQt5.QtCore import QRect, Qt
import pandas as pd
import yfinance as yf
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.pyplot as plt

# Removed API_KEY and requests as we're using yfinance exclusively

def get_stock_overview(symbol):
    stock = yf.Ticker(symbol)
    try:
        info = stock.info
        return info
    except Exception as e:
        return {}

def get_current_price(symbol):
    stock = yf.Ticker(symbol)
    try:
        data = stock.history(period='1d')
        if not data.empty:
            return data['Close'][0]
        else:
            return None
    except Exception as e:
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



class TextWrappingHeader(QHeaderView):
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setSectionsClickable(True)
        self.sectionResized.connect(self.on_sectionResized)

    def on_sectionResized(self, logicalIndex, oldSize, newSize):
        self.viewport().update()

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        painter.translate(rect.topLeft())
        text = self.model().headerData(logicalIndex, self.orientation(), Qt.DisplayRole)
        option = QStyleOptionHeader()
        self.initStyleOption(option)
        option.rect = QRect(0, 0, rect.width(), rect.height())
        option.text = ''
        style = self.style()
        style.drawControl(QStyle.CE_Header, option, painter, self)
        textRect = style.subElementRect(QStyle.SE_HeaderLabel, option, self)
        textRect.adjust(4, 4, -4, -4)
        doc = QTextDocument()
        doc.setTextWidth(textRect.width())
        doc.setDefaultFont(self.font())
        doc.setPlainText(text)
        painter.translate(textRect.topLeft())
        clip = QRectF(0, 0, textRect.width(), textRect.height())  # Use QRectF
        doc.drawContents(painter, clip)
        painter.restore()



class DividendTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Dividend Tracker')
        self.setGeometry(100, 100, 1200, 800)
        self.portfolio = []
        self.dividend_history = []
        self.initUI()
        # Keep references to child windows to prevent them from being garbage collected
        self.allocation_window = None
        self.calendar_window = None
        self.report_window = None
        self.dividend_window = None

    def initUI(self):
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main Layout
        self.main_layout = QVBoxLayout()

        # Portfolio Summary Section
        self.summary_layout = QGridLayout()
        self.create_portfolio_summary()
        self.main_layout.addLayout(self.summary_layout)

        # Holdings Table
        self.create_holdings_table()
        self.main_layout.addWidget(self.table)

        # Portfolio Ratios Section
        self.ratios_layout = QGridLayout()
        self.create_portfolio_ratios()
        self.main_layout.addLayout(self.ratios_layout)

        # Buttons
        self.buttons_layout = QHBoxLayout()
        self.create_buttons()
        self.main_layout.addLayout(self.buttons_layout)

        # Set main layout
        self.central_widget.setLayout(self.main_layout)

        # Menu Bar for Import/Export
        menubar = self.menuBar()
        file_menu = menubar.addMenu('File')

        import_portfolio_action = QAction('Import Portfolio', self)
        import_portfolio_action.triggered.connect(self.import_portfolio)
        file_menu.addAction(import_portfolio_action)

        export_portfolio_action = QAction('Export Portfolio', self)
        export_portfolio_action.triggered.connect(self.export_portfolio)
        file_menu.addAction(export_portfolio_action)

        # Add Import Transactions menu item
        import_transactions_action = QAction('Import Transactions', self)
        import_transactions_action.triggered.connect(self.import_transactions)
        file_menu.addAction(import_transactions_action)



    def create_portfolio_summary(self):
        # Labels for Portfolio Summary
        labels = [
            'Total Value ($):', 'Total Live ($):', 'Profit/Loss ($):', 'Profit/Loss + Dividends ($):',
            'Total Dividends ($):', 'Total Value (€):', 'Total Live (€):', 'Profit/Loss (€):',
            'Profit/Loss + Dividends (€):', 'Total Dividends (€):', 'Dividend % in Portfolio:'
        ]
        self.summary_values = {}
        for i, label_text in enumerate(labels):
            label = QLabel(label_text)
            value_label = QLabel('0.00')
            self.summary_layout.addWidget(label, i // 2, (i % 2) * 2)
            self.summary_layout.addWidget(value_label, i // 2, (i % 2) * 2 + 1)
            self.summary_values[label_text] = value_label

    def create_holdings_table(self):
        # Table Widget
        self.table = QTableWidget()
        self.table.setColumnCount(28)  # Increased from 25 to 28
        self.table.setHorizontalHeader(TextWrappingHeader(self.table))
        self.table.setHorizontalHeaderLabels([
            'Sector', 'Company Name', 'Ticker', '# of Shares', 'Avg Purchase Price',
            'Live Price', 'Book Value', 'Current Value', 'Profit/Loss ($)', 'Profit/Loss (%)',
            'Profit/Loss + Div ($)', 'Profit/Loss + Div (%)', 'Dividends Received ($)',
            'EUR Cash Invested', 'Current EUR Value', 'Profit/Loss (€)', 'Profit/Loss (%)',
            'Profit/Loss + Div (€)', 'Profit/Loss + Div (%)', 'Dividends Received (€)',
            'Current Div.Yield', 'Current Y-o-C', 'Actual Dividend Growth',
            'Portfolio Alloc % Book Value', 'Portfolio Alloc % Live Value', 'Sector Alloc % Book Value',
            'Sector Alloc % Live Value', '% Dividends in Portfolio'
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # Adjust the row height to accommodate wrapped text
        self.table.horizontalHeader().setFixedHeight(60)
        # Connect double-click signal to open detailed view
        self.table.itemDoubleClicked.connect(self.open_stock_details)


    def create_portfolio_ratios(self):
        # Labels for Portfolio Ratios
        labels = [
            'Dividend ROI %:', 'Yearly Portfolio Dividend Yield:', 'Portfolio Growth %:',
            'Monthly Dividend Growth %:', 'Year-on-Year Monthly Dividend Growth %:'
        ]
        self.ratio_values = {}
        for i, label_text in enumerate(labels):
            label = QLabel(label_text)
            value_label = QLabel('0.00%')
            self.ratios_layout.addWidget(label, i, 0)
            self.ratios_layout.addWidget(value_label, i, 1)
            self.ratio_values[label_text] = value_label

    def create_buttons(self):
        # Buttons
        self.calendar_button = QPushButton('Show Dividend Calendar')
        self.calendar_button.clicked.connect(self.show_dividend_calendar)
        self.projection_button = QPushButton('Show Income Projections')
        self.projection_button.clicked.connect(self.calculate_income_projections)
        self.report_button = QPushButton('Generate Income Report')
        self.report_button.clicked.connect(self.generate_income_report)
        self.allocation_button = QPushButton('Show Portfolio Allocation')
        self.allocation_button.clicked.connect(self.show_portfolio_allocation)
        self.dividend_history_button = QPushButton('Show Dividend History')
        self.dividend_history_button.clicked.connect(self.show_dividend_history)

        self.buttons_layout.addWidget(self.calendar_button)
        self.buttons_layout.addWidget(self.projection_button)
        self.buttons_layout.addWidget(self.report_button)
        self.buttons_layout.addWidget(self.allocation_button)
        self.buttons_layout.addWidget(self.dividend_history_button)

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
        if not overview:
            QMessageBox.warning(self, 'Symbol Error', f'No data found for symbol: {symbol}')
            return

        # Add to portfolio
        self.portfolio.append({
            'symbol': symbol,
            'company_name': overview.get('longName', ''),
            'sector': overview.get('sector', ''),
            'shares': shares,
            'cost_basis': cost_basis,
            'total_dividends': 0.0
        })

        # Clear input fields
        self.symbol_input.clear()
        self.shares_input.clear()
        self.cost_input.clear()

        # Update table and summaries
        self.update_table()
        self.update_portfolio_summary()
        self.update_portfolio_ratios()

    def update_table(self):
        self.table.setRowCount(0)  # Clear existing data
        total_book_value = 0
        total_current_value = 0
        total_dividends = 0
        sector_allocations = {}

        for stock in self.portfolio:
            symbol = stock['symbol']
            shares = stock['shares']
            cost_basis = stock['cost_basis']
            total_dividends += stock.get('total_dividends', 0.0)

            # Fetch current price and dividend data
            current_price = get_current_price(symbol)
            overview = get_stock_overview(symbol)
            if current_price is None:
                continue

            market_value = current_price * shares
            book_value = cost_basis * shares
            unrealized_gain = market_value - book_value
            unrealized_gain_percent = (unrealized_gain / book_value) * 100 if book_value > 0 else 0
            total_return = (unrealized_gain + stock.get('total_dividends', 0.0)) / book_value * 100 if book_value > 0 else 0

            dividend_per_share = float(overview.get('dividendRate', 0.0)) if overview.get('dividendRate') else 0.0
            annual_dividend = dividend_per_share * shares
            dividend_yield = (dividend_per_share / current_price) * 100 if current_price > 0 else 0.0

            # Current Yield on Cost
            current_yoc = (dividend_per_share / cost_basis) * 100 if cost_basis > 0 else 0.0

            # Calculate Actual Dividend Growth
            dividends_df = get_dividend_events(symbol)
            if not dividends_df.empty:
                dividends_df['Date'] = pd.to_datetime(dividends_df['Date'])
                dividends_df['Year'] = dividends_df['Date'].dt.year
                dividends_per_year = dividends_df.groupby('Year')['Dividend'].sum().sort_index()
                if len(dividends_per_year) >= 2:
                    last_year = dividends_per_year.index[-1]
                    prev_year = dividends_per_year.index[-2]
                    last_year_div = dividends_per_year[last_year]
                    prev_year_div = dividends_per_year[prev_year]
                    if prev_year_div != 0:
                        actual_dividend_growth = ((last_year_div - prev_year_div) / prev_year_div) * 100
                    else:
                        actual_dividend_growth = None
                else:
                    actual_dividend_growth = None
            else:
                actual_dividend_growth = None

            if actual_dividend_growth is not None:
                actual_dividend_growth_str = f"{actual_dividend_growth:.2f}%"
            else:
                actual_dividend_growth_str = 'N/A'

            # Currency conversions (Assuming 1 USD = 0.9 EUR for example)
            exchange_rate = 0.9  # Replace with actual rate or fetch dynamically
            eur_cash_invested = book_value * exchange_rate
            current_eur_value = market_value * exchange_rate
            eur_unrealized_gain = current_eur_value - eur_cash_invested
            eur_unrealized_gain_percent = (eur_unrealized_gain / eur_cash_invested) * 100 if eur_cash_invested > 0 else 0
            eur_total_return = (eur_unrealized_gain + stock.get('total_dividends', 0.0) * exchange_rate) / eur_cash_invested * 100 if eur_cash_invested > 0 else 0

            total_book_value += book_value
            total_current_value += market_value

            # Sector allocations
            sector = stock.get('sector', 'Unknown')
            sector_allocations.setdefault(sector, {'book_value': 0, 'current_value': 0})
            sector_allocations[sector]['book_value'] += book_value
            sector_allocations[sector]['current_value'] += market_value

            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            # Fill table with data
            data = [
                sector,
                stock.get('company_name', ''),
                symbol,
                f"{shares:.4f}",
                f"${cost_basis:.2f}",
                f"${current_price:.2f}",
                f"${book_value:.2f}",
                f"${market_value:.2f}",
                f"${unrealized_gain:.2f}",
                f"{unrealized_gain_percent:.2f}%",
                f"${unrealized_gain + stock.get('total_dividends', 0.0):.2f}",
                f"{total_return:.2f}%",
                f"${stock.get('total_dividends', 0.0):.2f}",
                f"€{eur_cash_invested:.2f}",
                f"€{current_eur_value:.2f}",
                f"€{eur_unrealized_gain:.2f}",
                f"{eur_unrealized_gain_percent:.2f}%",
                f"€{eur_unrealized_gain + stock.get('total_dividends', 0.0) * exchange_rate:.2f}",
                f"{eur_total_return:.2f}%",
                f"€{stock.get('total_dividends', 0.0) * exchange_rate:.2f}",
                f"{dividend_yield:.2f}%",
                f"{current_yoc:.2f}%",
                actual_dividend_growth_str,
                '',  # Portfolio Alloc % Book Value (to be calculated)
                '',  # Portfolio Alloc % Live Value (to be calculated)
                '',  # Sector Alloc % Book Value (to be calculated)
                '',  # Sector Alloc % Live Value (to be calculated)
                '',  # % Dividends in Portfolio
            ]
            for col, value in enumerate(data):
                self.table.setItem(row_position, col, QTableWidgetItem(value))

        # Calculate allocations
        for row in range(self.table.rowCount()):
            book_value = float(self.table.item(row, 6).text().replace('$', ''))
            market_value = float(self.table.item(row, 7).text().replace('$', ''))
            symbol = self.table.item(row, 2).text()
            sector = self.table.item(row, 0).text()

            # Portfolio Allocation %
            portfolio_alloc_book = (book_value / total_book_value * 100) if total_book_value > 0 else 0
            portfolio_alloc_live = (market_value / total_current_value * 100) if total_current_value > 0 else 0
            self.table.setItem(row, 23, QTableWidgetItem(f"{portfolio_alloc_book:.2f}%"))
            self.table.setItem(row, 24, QTableWidgetItem(f"{portfolio_alloc_live:.2f}%"))

            # Sector Allocation %
            sector_book_value = sector_allocations[sector]['book_value']
            sector_current_value = sector_allocations[sector]['current_value']
            sector_alloc_book = (book_value / sector_book_value * 100) if sector_book_value > 0 else 0
            sector_alloc_live = (market_value / sector_current_value * 100) if sector_current_value > 0 else 0
            self.table.setItem(row, 25, QTableWidgetItem(f"{sector_alloc_book:.2f}%"))
            self.table.setItem(row, 26, QTableWidgetItem(f"{sector_alloc_live:.2f}%"))

            # % Dividends in Portfolio
            total_dividends_row = float(self.table.item(row, 12).text().replace('$', ''))
            dividends_in_portfolio = (total_dividends_row / total_dividends) * 100 if total_dividends > 0 else 0
            self.table.setItem(row, 27, QTableWidgetItem(f"{dividends_in_portfolio:.2f}%"))

    def update_portfolio_summary(self):
        # Calculate summary values
        total_value_usd = sum(stock['cost_basis'] * stock['shares'] for stock in self.portfolio)
        total_live_usd = sum(get_current_price(stock['symbol']) * stock['shares'] for stock in self.portfolio if get_current_price(stock['symbol']) is not None)
        profit_loss_usd = total_live_usd - total_value_usd
        total_dividends_usd = sum(stock.get('total_dividends', 0.0) for stock in self.portfolio)
        profit_loss_with_dividends_usd = profit_loss_usd + total_dividends_usd

        # Currency conversion
        exchange_rate = 0.9  # Replace with actual rate or fetch dynamically
        total_value_eur = total_value_usd * exchange_rate
        total_live_eur = total_live_usd * exchange_rate
        profit_loss_eur = total_live_eur - total_value_eur
        total_dividends_eur = total_dividends_usd * exchange_rate
        profit_loss_with_dividends_eur = profit_loss_eur + total_dividends_eur

        # Dividend % in Portfolio
        dividend_percent_portfolio = (total_dividends_usd / total_value_usd * 100) if total_value_usd > 0 else 0

        # Update labels
        self.summary_values['Total Value ($):'].setText(f"${total_value_usd:.2f}")
        self.summary_values['Total Live ($):'].setText(f"${total_live_usd:.2f}")
        self.summary_values['Profit/Loss ($):'].setText(f"${profit_loss_usd:.2f}")
        self.summary_values['Profit/Loss + Dividends ($):'].setText(f"${profit_loss_with_dividends_usd:.2f}")
        self.summary_values['Total Dividends ($):'].setText(f"${total_dividends_usd:.2f}")
        self.summary_values['Total Value (€):'].setText(f"€{total_value_eur:.2f}")
        self.summary_values['Total Live (€):'].setText(f"€{total_live_eur:.2f}")
        self.summary_values['Profit/Loss (€):'].setText(f"€{profit_loss_eur:.2f}")
        self.summary_values['Profit/Loss + Dividends (€):'].setText(f"€{profit_loss_with_dividends_eur:.2f}")
        self.summary_values['Total Dividends (€):'].setText(f"€{total_dividends_eur:.2f}")
        self.summary_values['Dividend % in Portfolio:'].setText(f"{dividend_percent_portfolio:.2f}%")

    def update_portfolio_ratios(self):
        # Placeholder calculations (implement actual calculations based on your data)
        dividend_roi = 0.0
        yearly_dividend_yield = 0.0
        portfolio_growth = 0.0
        monthly_dividend_growth = 0.0
        yoy_monthly_dividend_growth = 0.0

        # Update labels
        self.ratio_values['Dividend ROI %:'].setText(f"{dividend_roi:.2f}%")
        self.ratio_values['Yearly Portfolio Dividend Yield:'].setText(f"{yearly_dividend_yield:.2f}%")
        self.ratio_values['Portfolio Growth %:'].setText(f"{portfolio_growth:.2f}%")
        self.ratio_values['Monthly Dividend Growth %:'].setText(f"{monthly_dividend_growth:.2f}%")
        self.ratio_values['Year-on-Year Monthly Dividend Growth %:'].setText(f"{yoy_monthly_dividend_growth:.2f}%")

    def process_transactions(self, df):
        # Process 'Market buy' transactions
        market_buys = df[df['Action'] == 'Market buy']
        for index, row in market_buys.iterrows():
            symbol = row['Ticker']
            shares = float(row['No. of shares'])
            total_cost = float(row['Total']) if pd.notnull(row['Total']) else 0.0
            currency_conversion_fee = float(row['Currency conversion fee']) if pd.notnull(row['Currency conversion fee']) else 0.0
            # Add currency conversion fee to total cost
            total_cost += currency_conversion_fee

            # Calculate cost basis per share
            cost_basis_per_share = total_cost / shares if shares != 0 else 0

            # Fetch company name and sector
            overview = get_stock_overview(symbol)
            company_name = overview.get('longName', '')
            sector = overview.get('sector', '')

            # Get exchange rate
            exchange_rate_str = row.get('Exchange rate', '')
            try:
                exchange_rate = float(exchange_rate_str)
            except (ValueError, TypeError):
                exchange_rate = 1.0  # Default exchange rate

            # Create a transaction record
            transaction = {
                'Purchase Date': pd.to_datetime(row['Time']).date(),
                'Order ID': row.get('ID', ''),
                'ISIN': row.get('ISIN', ''),
                'Purchase Price $': float(row['Price / share']) if pd.notnull(row['Price / share']) else 0.0,
                'Purchase Price €': total_cost,  # Assuming total_cost is in EUR
                'Qty. Shares': shares,
                'Value EUR': total_cost,
                'Currency exchange': exchange_rate,
                'Broker FX Fee EUR': currency_conversion_fee,
                'Consideration $': total_cost / exchange_rate if exchange_rate else total_cost
            }

            # Update portfolio
            found = False
            for stock in self.portfolio:
                if stock['symbol'] == symbol:
                    # Update shares and cost basis
                    total_shares = stock['shares'] + shares
                    # Calculate new average cost basis
                    total_cost_basis = (stock['shares'] * stock['cost_basis']) + total_cost
                    new_cost_basis_per_share = total_cost_basis / total_shares
                    stock['shares'] = total_shares
                    stock['cost_basis'] = new_cost_basis_per_share
                    # Append transaction
                    stock.setdefault('transactions', []).append(transaction)
                    found = True
                    break
            if not found:
                # Add new holding
                self.portfolio.append({
                    'symbol': symbol,
                    'company_name': company_name,
                    'sector': sector,
                    'shares': shares,
                    'cost_basis': cost_basis_per_share,
                    'total_dividends': 0.0,
                    'transactions': [transaction],
                    'dividends': []
                })

        # Process 'Dividend' transactions
        dividends = df[df['Action'].str.contains('Dividend', na=False)]
        for index, row in dividends.iterrows():
            symbol = row['Ticker']
            date = pd.to_datetime(row['Time']).date()
            amount = float(row['Total']) if pd.notnull(row['Total']) else 0.0

            # Create dividend record
            dividend_record = {
                'Date': date,
                'Dividend Received $': amount,
                'Dividend Received EUR': amount * 0.9,  # Assuming exchange rate
                'Comments': row.get('Notes', '')  # Adjusted from 'Comments' to 'Notes'
            }

            # Update total dividends in portfolio
            for stock in self.portfolio:
                if stock['symbol'] == symbol:
                    stock['total_dividends'] = stock.get('total_dividends', 0.0) + amount
                    # Append dividend record
                    stock.setdefault('dividends', []).append(dividend_record)
                    break
            else:
                # If the stock is not in the portfolio, you might want to add it or skip
                pass

        # Update the table and summaries
        self.update_table()
        self.update_portfolio_summary()
        self.update_portfolio_ratios()

    def import_portfolio(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Portfolio", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_name:
            try:
                df = pd.read_csv(file_name)
                # Expecting columns: symbol, shares, cost_basis
                if not {'symbol', 'shares', 'cost_basis'}.issubset(df.columns):
                    QMessageBox.warning(
                        self, 'Import Error', 'CSV file must contain symbol, shares, and cost_basis columns.'
                    )
                    return
                self.portfolio = df.to_dict('records')

                # Update the table and summaries
                self.update_table()
                self.update_portfolio_summary()
                self.update_portfolio_ratios()
            except Exception as e:
                QMessageBox.warning(
                    self, 'Import Error', f'An error occurred while importing the portfolio:\n{str(e)}'
                )

    def import_transactions(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Import Transactions", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_name:
            try:
                df = pd.read_csv(file_name)
                # Process transactions
                self.process_transactions(df)
                QMessageBox.information(
                    self, 'Import Successful', 'Transactions imported successfully.'
                )
            except Exception as e:
                QMessageBox.warning(
                    self, 'Import Error', f'An error occurred while importing the transactions:\n{str(e)}'
                )

    def show_dividend_calendar(self):
        # Collect all dividend events
        all_dividends = []

        # Include imported dividend transactions
        if self.dividend_history:
            df_dividends = pd.DataFrame(self.dividend_history)
            df_dividends['Date'] = pd.to_datetime(df_dividends['Date'])
            all_dividends.append(df_dividends)

        for stock in self.portfolio:
            symbol = stock['symbol']
            shares = stock['shares']

            dividends = get_dividend_events(symbol)
            if not dividends.empty:
                dividends['Symbol'] = symbol
                dividends['Dividend'] = dividends['Dividend'] * shares
                all_dividends.append(dividends)

        if not all_dividends:
            QMessageBox.information(self, 'Dividend Calendar', 'No dividend data available.')
            return

        df = pd.concat(all_dividends)
        df.sort_values('Date', inplace=True)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        # Show in a new window with a table
        self.calendar_window = QWidget()
        self.calendar_window.setWindowTitle('Dividend Calendar')
        layout = QVBoxLayout()
        table = QTableWidget()
        table.setRowCount(len(df))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Date', 'Symbol', 'Dividend Amount'])
        for i, row in df.iterrows():
            table.setItem(i, 0, QTableWidgetItem(row['Date']))
            table.setItem(i, 1, QTableWidgetItem(row['Symbol']))
            table.setItem(i, 2, QTableWidgetItem(f"${row['Dividend']:.2f}"))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        self.calendar_window.setLayout(layout)
        self.calendar_window.show()

    def calculate_income_projections(self):
        total_annual_dividend = 0
        projections = []

        for stock in self.portfolio:
            symbol = stock['symbol']
            shares = stock['shares']

            # Fetch dividend per share
            overview = get_stock_overview(symbol)
            dividend_per_share = float(overview.get('dividendRate', 0.0)) if overview.get('dividendRate') else 0.0

            annual_dividend = dividend_per_share * shares
            total_annual_dividend += annual_dividend

            projections.append({'symbol': symbol, 'annual_dividend': annual_dividend})

        # Include imported dividend transactions
        total_imported_dividends = sum(item['Dividend'] for item in self.dividend_history)
        total_annual_dividend += total_imported_dividends

        # Show results in a message box
        message = f"Total Annual Dividend Income: ${total_annual_dividend:.2f}\n\n"
        message += "Breakdown:\n"
        for proj in projections:
            message += f"{proj['symbol']}: ${proj['annual_dividend']:.2f}\n"
        if total_imported_dividends > 0:
            message += f"Imported Dividends: ${total_imported_dividends:.2f}\n"

        QMessageBox.information(self, 'Income Projections', message)

    def generate_income_report(self):
        total_annual_dividend = 0
        projections = []

        for stock in self.portfolio:
            symbol = stock['symbol']
            shares = stock['shares']

            # Fetch dividend per share
            overview = get_stock_overview(symbol)
            dividend_per_share = float(overview.get('dividendRate', 0.0)) if overview.get('dividendRate') else 0.0

            annual_dividend = dividend_per_share * shares
            total_annual_dividend += annual_dividend

            projections.append({
                'Symbol': symbol,
                'Shares': shares,
                'Dividend Per Share': dividend_per_share,
                'Annual Dividend': annual_dividend
            })

        # Include imported dividend transactions
        if self.dividend_history:
            df_dividends = pd.DataFrame(self.dividend_history)
            total_imported_dividends = df_dividends['Dividend'].sum()
            total_annual_dividend += total_imported_dividends
            projections.append({
                'Symbol': 'Imported Dividends',
                'Shares': '',
                'Dividend Per Share': '',
                'Annual Dividend': total_imported_dividends
            })

        # Convert to DataFrame
        df = pd.DataFrame(projections)

        # Ask user to select a file to save the report
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Income Report", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_name:
            try:
                df.to_csv(file_name, index=False)
                QMessageBox.information(
                    self, 'Report Generated', f'Income report saved to {file_name}'
                )
            except Exception as e:
                QMessageBox.warning(
                    self, 'Report Error', f'An error occurred while saving the report:\n{str(e)}'
                )
        else:
            QMessageBox.information(self, 'Report Cancelled', 'Income report generation cancelled.')

    def show_portfolio_allocation(self):
        # Calculate total market value and allocation
        allocation = {}
        total_value = 0
        for stock in self.portfolio:
            symbol = stock['symbol']
            shares = stock['shares']
            current_price = get_current_price(symbol)
            if current_price is not None:
                market_value = current_price * shares
                allocation[symbol] = market_value
                total_value += market_value
            else:
                allocation[symbol] = 0

        if total_value == 0:
            QMessageBox.warning(self, 'Allocation Error', 'Total market value is zero.')
            return

        # Prepare data for pie chart
        labels = list(allocation.keys())
        sizes = [value / total_value * 100 for value in allocation.values()]

        # Plot pie chart
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        ax.axis('equal')
        ax.set_title('Portfolio Allocation')

        # Show in a new window
        canvas = FigureCanvasQTAgg(fig)
        self.allocation_window = QWidget()
        allocation_layout = QVBoxLayout()
        allocation_layout.addWidget(canvas)
        self.allocation_window.setLayout(allocation_layout)
        self.allocation_window.setWindowTitle('Portfolio Allocation')
        self.allocation_window.show()
        canvas.draw()

    def export_portfolio(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Portfolio", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_name:
            try:
                df = pd.DataFrame(self.portfolio)
                df.to_csv(file_name, index=False)
                QMessageBox.information(
                    self, 'Export Successful', f'Portfolio exported successfully to {file_name}'
                )
            except Exception as e:
                QMessageBox.warning(
                    self, 'Export Error', f'An error occurred while exporting the portfolio:\n{str(e)}'
                )

    def show_dividend_history(self):
        if not self.dividend_history:
            QMessageBox.information(self, 'Dividend History', 'No dividend history available.')
            return

        df = pd.DataFrame(self.dividend_history)
        df.sort_values('Date', inplace=True)
        df['Date'] = df['Date'].astype(str)

        # Show in a new window with a table
        self.dividend_window = QWidget()
        self.dividend_window.setWindowTitle('Dividend History')
        layout = QVBoxLayout()
        table = QTableWidget()
        table.setRowCount(len(df))
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(['Date', 'Symbol', 'Dividend Amount'])
        for i, row in df.iterrows():
            table.setItem(i, 0, QTableWidgetItem(row['Date']))
            table.setItem(i, 1, QTableWidgetItem(row['Symbol']))
            table.setItem(i, 2, QTableWidgetItem(f"${row['Dividend']:.2f}"))
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(table)
        self.dividend_window.setLayout(layout)
        self.dividend_window.show()

    def open_stock_details(self, item):
        row = item.row()
        symbol = self.table.item(row, 2).text()  # Assuming the 'Ticker' column is at index 2
        # Find the stock data
        stock_data = next((stock for stock in self.portfolio if stock['symbol'] == symbol), None)
        if stock_data:
            self.stock_detail_window = StockDetailWindow(stock_data)
            self.stock_detail_window.show()

class StockDetailWindow(QWidget):
    def __init__(self, stock_data):
        super().__init__()
        self.setWindowTitle(f"Details for {stock_data['symbol']}")
        self.stock_data = stock_data
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Display calculated metrics
        metrics_layout = QGridLayout()
        metrics = self.calculate_metrics()
        row = 0
        for key, value in metrics.items():
            metrics_layout.addWidget(QLabel(f"{key}:"), row, 0)
            metrics_layout.addWidget(QLabel(str(value)), row, 1)
            row += 1
        layout.addLayout(metrics_layout)

        # Transactions Table
        transactions_label = QLabel("Transactions:")
        layout.addWidget(transactions_label)
        transactions_table = QTableWidget()
        transactions_table.setColumnCount(8)
        transactions_table.setHorizontalHeaderLabels([
            'Purchase Date', 'Order ID', 'ISIN', 'Purchase Price $',
            'Purchase Price €', 'Qty. Shares', 'Value EUR', 'Broker FX Fee EUR'
        ])
        transactions = self.stock_data.get('transactions', [])
        transactions_table.setRowCount(len(transactions))
        for i, txn in enumerate(transactions):
            transactions_table.setItem(i, 0, QTableWidgetItem(str(txn['Purchase Date'])))
            transactions_table.setItem(i, 1, QTableWidgetItem(txn['Order ID']))
            transactions_table.setItem(i, 2, QTableWidgetItem(txn['ISIN']))
            transactions_table.setItem(i, 3, QTableWidgetItem(f"${txn['Purchase Price $']:.2f}"))
            transactions_table.setItem(i, 4, QTableWidgetItem(f"€{txn['Purchase Price €']:.2f}"))
            transactions_table.setItem(i, 5, QTableWidgetItem(f"{txn['Qty. Shares']}"))
            transactions_table.setItem(i, 6, QTableWidgetItem(f"€{txn['Value EUR']:.2f}"))
            transactions_table.setItem(i, 7, QTableWidgetItem(f"€{txn['Broker FX Fee EUR']:.2f}"))
        transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(transactions_table)

        # Dividends Table
        dividends_label = QLabel("Dividends:")
        layout.addWidget(dividends_label)
        dividends_table = QTableWidget()
        dividends_table.setColumnCount(4)
        dividends_table.setHorizontalHeaderLabels([
            'Date', 'Dividend Received $', 'Dividend Received EUR', 'Comments'
        ])
        dividends = self.stock_data.get('dividends', [])
        dividends_table.setRowCount(len(dividends))
        for i, div in enumerate(dividends):
            dividends_table.setItem(i, 0, QTableWidgetItem(str(div['Date'])))
            dividends_table.setItem(i, 1, QTableWidgetItem(f"${div['Dividend Received $']:.2f}"))
            dividends_table.setItem(i, 2, QTableWidgetItem(f"€{div['Dividend Received EUR']:.2f}"))
            comments = div.get('Comments', '')
            if pd.isna(comments):
                comments = ''
            dividends_table.setItem(i, 3, QTableWidgetItem(comments))
        dividends_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(dividends_table)

        self.setLayout(layout)

    def calculate_metrics(self):
        # Perform calculations similar to the data you provided

        average_purchase_price = self.stock_data['cost_basis']
        total_shares = self.stock_data['shares']
        current_price = get_current_price(self.stock_data['symbol'])

        # USD Calculations
        total_value_usd = sum(txn['Consideration $'] for txn in self.stock_data.get('transactions', []))
        current_value_usd = current_price * total_shares
        profit_loss_usd = current_value_usd - total_value_usd
        profit_loss_percent_usd = (profit_loss_usd / total_value_usd) * 100 if total_value_usd else 0
        total_dividends_usd = self.stock_data.get('total_dividends', 0.0)
        profit_loss_with_dividends_usd = profit_loss_usd + total_dividends_usd
        total_profit_loss_percent_usd = (profit_loss_with_dividends_usd / total_value_usd) * 100 if total_value_usd else 0

        # EUR Calculations (assuming exchange rate)
        exchange_rate = 0.9  # Adjust exchange rate as needed
        total_value_eur = total_value_usd * exchange_rate
        current_value_eur = current_value_usd * exchange_rate
        profit_loss_eur = current_value_eur - total_value_eur
        profit_loss_percent_eur = (profit_loss_eur / total_value_eur) * 100 if total_value_eur else 0
        total_dividends_eur = total_dividends_usd * exchange_rate
        profit_loss_with_dividends_eur = profit_loss_eur + total_dividends_eur
        total_profit_loss_percent_eur = (profit_loss_with_dividends_eur / total_value_eur) * 100 if total_value_eur else 0

        # Build the metrics dictionary
        metrics = {
            'Average Purchase Price $': f"${average_purchase_price:.2f}",
            'Total Shares': total_shares,
            'Live Price $': f"${current_price:.2f}",

            'Total Value $': f"${total_value_usd:.2f}",
            'Current Value $': f"${current_value_usd:.2f}",
            'Profit/Loss (price) $': f"${profit_loss_usd:.2f}",
            'Profit/Loss (%) $': f"{profit_loss_percent_usd:.2f}%",
            'Profit/Loss + Dividends $': f"${profit_loss_with_dividends_usd:.2f}",
            'Total Profit/Loss (%) $': f"{total_profit_loss_percent_usd:.2f}%",

            'Total Value €': f"€{total_value_eur:.2f}",
            'Current Value €': f"€{current_value_eur:.2f}",
            'Profit/Loss (price) €': f"€{profit_loss_eur:.2f}",
            'Profit/Loss (%) €': f"{profit_loss_percent_eur:.2f}%",
            'Profit/Loss + Dividends €': f"€{profit_loss_with_dividends_eur:.2f}",
            'Total Profit/Loss (%) €': f"{total_profit_loss_percent_eur:.2f}%"
        }

        return metrics



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = DividendTracker()
    window.show()
    sys.exit(app.exec_())
