import datetime
import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from joblib import Parallel, delayed
import pandas as pd
from ibapi.account_summary_tags import AccountSummaryTags
from ibapi.client import EClient, TickerId
from ibapi.common import BarData, OrderId, TickAttribBidAsk
from ibapi.contract import Contract, ContractDetails
from ibapi.decoder import TickType, TickTypeEnum
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.utils import decimalMaxString, floatMaxString
from ibapi.wrapper import EWrapper
from ibapi.execution import ExecutionFilter, Execution
from ibapi.commission_report import CommissionReport
from requests import request
from market_data.quotes import Quote
from data_requests import DataRequest, Subscription
from market_data.ust_bonds import get_bonds_info
from strategy.orders import StrategyOrder, create_market_order
from others import df_to_tt, estimate_bond_name
from strategy.pairs_trade import PairsTrade, check_bonds
from strategy.parameters import StrategyParameters
from strategy.positions import StrategyPosition
from market_data.ust_bonds import USTreasurySecurity
from market_data.historical import PriceBar
from strategy.status import StrategyStatus
from strategy.pairs_trade import is_cointegrated
from log_config import log

@dataclass
class TradingApp(EWrapper, EClient):
    def __init__(self, account: str,bar_interval:int,rolling_window:int, percent_of_account_to_use: float = 100):
        EClient.__init__(self, self)
        self.account = account
        self.bar_interval = bar_interval
        self.rolling_window = rolling_window
        self.buying_powers: dict[str, float] = {}
        self.bonds_general_info: list[USTreasurySecurity] = []
        self.historical_data: dict[str, list[PriceBar]] = {}
        self.requests: dict[int, Subscription] = {}
        self.errors: list[str] = []
        self.request_counter: int = 1
        self.strategy_data: Optional[StrategyParameters] = None
        self.quotes: dict[int, Quote] = {}
        self.positions: dict[int, StrategyPosition] = {}
        self.pinged_positions = False
        self.status = StrategyStatus.INITIALIZED
        self.next_valid_order_id: Optional[int] = None
        self.orders: dict[int, StrategyOrder] = {}
        self.last_update_time: float = datetime.datetime.now().timestamp()
        self.account_summary_provided: bool = False
        self.position_quotes_complete: bool = False
        self.orders_received: bool = False
        self.number_complete_historical_datasets = 0
        self.requests_locked: bool = False
        self.orders_locked: bool = False
        self.percent_of_account_to_use = percent_of_account_to_use
        self.trades: list[PairsTrade] = []
        self.previous_spread: Optional[float] = None
        self.start_time: float = datetime.datetime.now()

    def generate_req_id(self) -> int:
        out = self.request_counter
        self.request_counter += 1
        return out

    def seconds_since_start(self) -> float:
        return (datetime.datetime.now() - self.start_time).total_seconds()

    def nextValidId(self, orderId: int):
        self.next_valid_order_id = orderId
        return super().nextValidId(orderId)

    def get_next_valid_order_id(self) -> int:
        if self.orders:
            return max([self.next_valid_order_id+1, max([id for id in self.orders.keys()])]) + 1
        else:
            return self.next_valid_order_id + 1

    def error(self, reqId, errorCode, errorString, contract=None):
        # check if the errorCode starts with 21
        is_warning = str(errorCode)[:2] == '21'
        is_error = False if reqId == -1 else True
        if reqId in self.requests:
            name = self.requests[reqId].name
        else:
            name = 'General'
        if is_error:
            log.error(f'{name}: {errorString}')
        if is_warning:
            log.warning(f'{name}: {errorString}')

    def profit_target(self) -> Optional[float]:
        if self.positions:
            sizes: list[float] = [abs(float(position.quantity))
                                for position in self.positions.values()]
            includes_bonds = any([position.contract.secType == 'BOND' for position in self.positions.values()])
            pt = self.strategy_data.spread_std*min(sizes)
            if includes_bonds:
                return 10*pt
            return pt
        else:
            return None

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        return super().contractDetails(reqId, contractDetails)

    def update_status(self, new_status: StrategyStatus):
        if self.status != new_status:
            log.info(f'Status Update: {self.status} -> {new_status}')
            self.status = new_status

    def positionEnd(self):
        table = self.produce_positions_table()
        if table:
            log.info(f'Positions: \n{table}')
        return super().positionEnd()

    def produce_positions_table(self) -> Optional[str]:
        if self.is_flat():
            return None
        rows = []
        for position in self.positions.values():
            rows.append(position.to_row())
        table = pd.DataFrame(rows)
        tt = df_to_tt(table)
        return tt

    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        self.pinged_positions = True
        if position != 0 and account == self.account:
            if contract.secType == 'BOND':
                ltd = datetime.datetime.strptime(
                    contract.lastTradeDateOrContractMonth, '%Y%m%d').date()
                name = estimate_bond_name(ltd)
                cusip = '-'
                for bond in self.bonds_general_info:
                    if bond.securityTerm == name or bond.maturityDate == ltd:
                        cusip = bond.cusip
                        break
                avg_price = 0.1*float(floatMaxString(avgCost))
            else:
                avg_price = float(floatMaxString(avgCost))
            contract.exchange = 'SMART'
            self.positions[contract.conId] = StrategyPosition(
                contract, name, cusip, account, avg_price, float(position))
        return super().position(account, contract, position, avgCost)

    def true_unrealized_pnl_all(self) -> float:
        pnl: float = 0
        copy = self.positions.copy()
        if len(copy) == 2:
            for position in copy.values():
                if position.contract.conId in self.quotes:
                    if self.quotes[position.contract.conId].is_valid(5.0):
                        this_pnl = position.unrealized_pnl(
                            self.quotes[position.contract.conId])
                        if this_pnl:
                            pnl += this_pnl
        return pnl

    def close_all_positions(self):
        if not self.is_flat():
            for position in self.positions.values():
                if not position.closing_order_sent:
                    new_contract = position.contract
                    new_contract.exchange = 'SMART'
                    order = position.create_closing_order()
                    strategy_order = StrategyOrder.create(order, new_contract)
                    id = self.get_next_valid_order_id()
                    self.orders[id] = strategy_order
        self.send_strategy_orders()
    ### -------- orders --------######

    def orderStatus(self, orderId: OrderId, status: str, filled: Decimal, remaining: Decimal, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCselfrice: float):
        if orderId in self.orders:
            self.orders[orderId].status = status
            self.orders[orderId].fill_price = avgFillPrice
            if status == 'Filled' and self.orders[orderId].order.totalQuantity == filled and remaining == 0:
                ltd = datetime.datetime.strptime(
                    self.orders[orderId].contract.lastTradeDateOrContractMonth, '%Y%m%d').date()
                name = estimate_bond_name(ltd)
                cusip = '-'
                for bond in self.bonds_general_info:
                    if bond.contract_details:
                        if self.orders[orderId].contract.conId == bond.contract_details.contract.conId:
                            cusip = bond.cusip
                self.orders[orderId].fill_time = datetime.datetime.now(
                ).timestamp()
                if self.status == StrategyStatus.SENT_ENTRY_ORDERS:
                    self.positions[self.orders[orderId].contract.conId] = StrategyPosition.from_filled_order(
                        self.orders[orderId].order, self.orders[orderId].contract, avgFillPrice, name=name, cusip=cusip)
                    if not self.trades:
                        self.trades.append(
                            PairsTrade.open(self.orders[orderId]))
                    else:
                        if self.trades[-1].is_complete():
                            self.trades.append(
                                PairsTrade.open(self.orders[orderId]))
                        else:
                            self.trades[-1].add_entry_order(
                                self.orders[orderId])
                if self.status == StrategyStatus.SENT_EXIT_ORDERS:
                    if self.orders[orderId].contract.conId in self.positions:
                        self.positions.pop(self.orders[orderId].contract.conId)
                        if self.trades:
                            self.trades[-1].add_exit_order(self.orders[orderId])
        return super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCselfrice)

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        self.orders[orderId] = StrategyOrder(
            order, contract, orderState.status, None, None, None)

    def send_strategy_orders(self):
        for orderId, order in self.orders.items():
            if order.status == 'Unsent' and order.contract:
                new_contract = order.contract
                new_contract.exchange = 'SMART'
                self.placeOrder(orderId, new_contract, order.order)
                order.sent_time = datetime.datetime.now().timestamp()
                order.status = 'Sent'

    def calculate_position_sizes(self) -> tuple[int, int]:
        total_money_available = self.buying_powers[self.account]*(
            self.percent_of_account_to_use/100)
        one_thousand_dollar_units = math.floor(total_money_available/1000)
        if self.strategy_data.hedge_ratio < 1:
            contract_1_amount = math.floor(0.5*one_thousand_dollar_units)
            contract_2_amount = math.floor(self.strategy_data.hedge_ratio*contract_1_amount)
        else:
            contract_2_amount = math.floor(0.5*one_thousand_dollar_units)
            contract_1_amount = math.floor(contract_2_amount/self.strategy_data.hedge_ratio)
        return [contract_1_amount, contract_2_amount]

    # def calculate_position_sizes_testing(self, sell_contract: int) -> tuple[int, int]:
    #     if sell_contract == 1:
    #         contract_1_amount = 5000
    #         contract_2_amount = math.floor(
    #             contract_1_amount/self.strategy_data.hedge_ratio)
    #     else:
    #         contract_2_amount = 5000
    #         contract_1_amount = math.floor(
    #             contract_2_amount*self.strategy_data.hedge_ratio)
    #     return [contract_1_amount, contract_2_amount]

    def openOrderEnd(self):
        self.orders_received = True
        rows = []
        for _, order in self.orders.items():
            rows.append(order.get_summary())
        df = pd.DataFrame(rows)
        tt = df_to_tt(df)
        if not df.empty:
            print(tt)
        return super().openOrderEnd()

    def has_open_orders(self) -> bool:
        if self.orders:
            is_open = True
            for _, order in self.orders.items():
                is_open = is_open and order.is_open()
            return is_open
        else:
            return False

    ### -------- end orders --------######

    def is_flat(self) -> bool:
        return not self.positions

    def bondContractDetails(self, reqId: int, contractDetails: ContractDetails):
        for bond in self.bonds_general_info:
            if self.requests[reqId].name == bond.securityTerm:
                bond.contract_details = contractDetails
        return super().bondContractDetails(reqId, contractDetails)

    def tickByTickBidAsk(self, reqId: int, time: int, bidPrice: float, askPrice: float, bidSize: Decimal, askSize: Decimal, tickAttribBidAsk: TickAttribBidAsk):
        if reqId in self.requests:
            name = self.requests[reqId].contract.conId
            mid_price = round((bidPrice + askPrice)/2,3)
            self.quotes[name] = Quote(bidPrice,askPrice,bidSize,askSize,mid_price,time)
        return super().tickByTickBidAsk(reqId, time, bidPrice, askPrice, bidSize, askSize, tickAttribBidAsk)
    ###---------------Historical Data-----------------###

    def historicalData(self, reqId: int, bars: BarData):
        if reqId in self.requests:
            name = self.requests[reqId].name
            bar = PriceBar.from_bar_data(bars)
            if name in self.historical_data:
                self.historical_data[name].append(bar)
            else:
                self.historical_data[name] = [bar]
        return super().historicalData(reqId, bars)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        self.number_complete_historical_datasets += 1
        if reqId in self.requests:
            name = self.requests[reqId].name
            if name in self.historical_data:
                self.historical_data[name].sort(key=lambda x: x.timestamp)
            log.info(f'Obtained {len(self.historical_data[name])} bars for the {name}')

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        if reqId in self.requests:
            name = self.requests[reqId].name
            if name in self.historical_data:
                price_bar = PriceBar.from_bar_data(bar)
                if self.historical_data[name][-1].timestamp != price_bar.timestamp:
                    self.historical_data[name].append(price_bar)
                    if self.strategy_data and name in [self.strategy_data.bond_1_name, self.strategy_data.bond_2_name] and self.historical_data[self.strategy_data.bond_1_name][-1].timestamp == self.historical_data[self.strategy_data.bond_2_name][-1].timestamp:
                        parameters = check_bonds(self.strategy_data.bond_1_name,self.historical_data[self.strategy_data.bond_1_name],self.strategy_data.bond_2_name,self.historical_data[self.strategy_data.bond_2_name],self.strategy_data.rolling_window)
                        if parameters['complete_coint']:
                            self.strategy_data.spread_mean = parameters['spread_mean']
                            self.strategy_data.spread_std = parameters['spread_std']
                        elif parameters['complete_coint'] is False:
                            self.strategy_data = None
                            log.error('Cointegration failed, strategy data reset')
                            self.update_status(StrategyStatus.ANALYZING_PAIRS)
                        log.info(f'Updated strategy parameters hedge ratio {self.strategy_data.hedge_ratio}, mean {self.strategy_data.spread_mean}, std {self.strategy_data.spread_std}, reversion time {self.strategy_data.time_to_revert}')

        return super().historicalDataUpdate(reqId, bar)
    ##-----------------ACCOUNT DATA-------------------##

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        if self.status == StrategyStatus.INITIALIZED:
            log.info(f'Account <{account}> buying power {value} {currency}')
        if tag == 'BuyingPower':
            self.buying_powers[account] = float(value)

    def accountSummaryEnd(self, reqId: int):
        self.account_summary_provided = True
        return super().accountSummaryEnd(reqId)

    ##-----------------Quote Data-------------------##
    def tickPrice(self, reqId: int, tickType: int, price: float, attrib: TickAttribBidAsk):
        if reqId in self.requests:
            name = self.requests[reqId].contract.conId
            if tickType == TickTypeEnum.BID or tickType == TickTypeEnum.ASK:
                if name in self.quotes:
                    if name:
                        self.quotes[name].update_quote(tickType, price)
                else:
                    if name:
                        self.quotes[name] = Quote.from_tick(tickType, price)
        return super().tickPrice(reqId, tickType, price, attrib)

    def tickSize(self, reqId: TickerId, tickType: TickType, size: Decimal):
        if reqId in self.requests:
            name = self.requests[reqId].contract.conId
            if (tickType == TickTypeEnum.BID_SIZE or tickType == TickTypeEnum.ASK_SIZE) and name in self.quotes and name is not None:
                self.quotes[name].update_quote(
                    tickType, float(floatMaxString(size)))
        return super().tickSize(reqId, tickType, size)

    ##-----------------Subscription and request Data-------------------##
    def subscribe_to_data(self, request_number: int, contract: Optional[Contract] = None, data_type: Optional[DataRequest] = None):
        match data_type:
            case DataRequest.ContractInfo:
                self.reqContractDetails(request_number, contract)
            case DataRequest.QuoteData:
                self.reqMktData(request_number, contract, '', False, False, [])
            case DataRequest.MarketDepth:
                self.reqMktDepth(request_number, contract, 10)
            case DataRequest.TickData:
                self.reqTickByTickData(
                    request_number, contract, "BidAsk", 1, False)
            case DataRequest.HistoricalData:
                request_name = f'{self.bar_interval} mins' if self.bar_interval > 1 else '1 min'
                self.reqHistoricalData(
                    request_number, contract, '', "1 M", request_name, 'MIDPOINT', 0, 1, True, [])
            case DataRequest.Positions:
                self.reqPositions()
            case DataRequest.Orders:
                self.reqOpenOrders()
            case DataRequest.Account:
                self.reqAccountSummary(
                    request_number, 'All', AccountSummaryTags.BuyingPower)
            case DataRequest.Executions:
                self.reqExecutions(request_number, ExecutionFilter())

        return request_number

    ##-----------------Spread Data-------------------##
    def calculate_spread(self) -> Optional[float]:
        if self.strategy_data:
            if self.strategy_data.bond_1_contract_id in self.quotes and self.strategy_data.bond_2_contract_id in self.quotes:
                spread = round(self.quotes[self.strategy_data.bond_1_contract_id].mid_price -
                               self.strategy_data.hedge_ratio*self.quotes[self.strategy_data.bond_2_contract_id].mid_price, 4)
                return spread
        return None

    def calculate_true_spread(self, mid_price_spread_above_avg: bool) -> Optional[float]:
        """True spread is calculated with bid and ask price."""
        if mid_price_spread_above_avg:
            true_spread = self.quotes[self.strategy_data.bond_1_contract_id].bid_price - (
                self.strategy_data.hedge_ratio)*self.quotes[self.strategy_data.bond_2_contract_id].ask_price
        else:
            true_spread = self.quotes[self.strategy_data.bond_1_contract_id].ask_price - (
                self.strategy_data.hedge_ratio)*self.quotes[self.strategy_data.bond_2_contract_id].bid_price
        return round(true_spread, 4)

    def send_requests(self):
        for request_id, request in self.requests.items():
            if not request.was_sent:
                request.was_sent = True
                self.subscribe_to_data(
                    request_id, request.contract, request.data_type)
                request.send_time = datetime.datetime.now(
                ).timestamp()
                log.info(f'{request.name} {request.data_type} request #{request_id} succesfully sent')

    ### --------------------Helper Functions --------------------###

    def has_all_data_to_calculate_strategy(self) -> bool:
        if self.strategy_data:
            if self.strategy_data.bond_1_contract_id in self.quotes and self.strategy_data.bond_2_contract_id in self.quotes:
                return True
        return False

    def received_all_account_data(self, positions_timeout: bool) -> bool:
        return (self.account in self.buying_powers or self.account_summary_provided) and (self.pinged_positions or positions_timeout) and self.orders_received

    def has_data_to_analyze_pairs(self) -> bool:
        return len(self.bonds_general_info) == (self.number_complete_historical_datasets)

    def has_data_to_place_trades(self) -> bool:
        if self.strategy_data and self.account in self.buying_powers:
            if self.strategy_data.bond_1_contract_id in self.quotes and self.strategy_data.bond_2_contract_id in self.quotes:
                if self.quotes[self.strategy_data.bond_1_contract_id].is_valid(5.0) and self.quotes[self.strategy_data.bond_2_contract_id].is_valid(5.0):
                    return True
        return False

    def has_data_to_calculate_spread(self) -> bool:
        if self.strategy_data:
            if self.strategy_data.bond_1_contract_id in self.quotes and self.strategy_data.bond_2_contract_id in self.quotes:
                return True
        return False

    def has_data_to_calculate_unrealized_pnl(self) -> bool:
        # we copy positions to avoid runtime error of accessing the same object
        positions_copy = self.positions.copy()
        for position in positions_copy.values():
            if position.contract.conId in self.quotes:
                if not self.quotes[position.contract.conId].is_valid(5.0):
                    return False
        return True

    def is_time_to_report(self, interval_in_seconds: int = 10) -> bool:
        now = datetime.datetime.now().timestamp()
        if (now - self.last_update_time) > interval_in_seconds:
            self.last_update_time = now
            return True
        else:
            return False

    def get_positions_table(self) -> str:
        if self.has_data_to_calculate_unrealized_pnl():
            rows = []
            for position in self.positions.values():
                rows.append(position.to_row_with_unrealized_pnl(
                    self.quotes[position.contract.conId]))
            df = pd.DataFrame(rows)
            df.loc[len(df)] = ['', '', '', '', '', '', '',
                               'total pnl', df.unrealized_pnl.sum()]
            table = df_to_tt(df)
            return table

    def buy_the_spread(self) -> None:
        contract_1_amount,contract_2_amount = self.calculate_position_sizes()
        sell_order = create_market_order(
            "SELL", contract_2_amount, self.account)
        buy_order = create_market_order(
            "BUY", contract_1_amount, self.account)
        id1 = self.get_next_valid_order_id()
        id2 = id1 + 1
        self.orders[id1] = StrategyOrder.create(
            sell_order, self.strategy_data.bond_1_contract)
        self.orders[id2] = StrategyOrder.create(
            buy_order, self.strategy_data.bond_2_contract)
        if not self.has_open_orders():
            self.send_strategy_orders()
        self.strategy_data.create_pickle_file()

    def sell_the_spread(self) -> None:
        contract_1_amount, contract_2_amount = self.calculate_position_sizes()
        sell_order = create_market_order(
            "SELL", contract_1_amount, self.account)
        buy_order = create_market_order(
            "BUY", contract_2_amount, self.account)
        id1 = self.get_next_valid_order_id()
        id2 = id1 + 1
        self.orders[id1] = StrategyOrder.create(
            sell_order, self.strategy_data.bond_1_contract)
        self.orders[id2] = StrategyOrder.create(
            buy_order, self.strategy_data.bond_2_contract)
        if not self.has_open_orders():
            self.send_strategy_orders()
        self.strategy_data.create_pickle_file()

    def find_pairs_trade(self) -> StrategyParameters:
        log.info(f'Finding pairs trade')
        names = [bond.securityTerm for bond in self.bonds_general_info]
        pairs = []
        for x in range(0, len(names)-1):
            for y in range(len(names)-1, 0, -1):
                if names[x] != names[y]:
                    pair = [names[x], names[y]]
                    reverse_pair = [names[y], names[x]]
                    if pair not in pairs:
                        pairs.append(pair)
                    if reverse_pair not in pairs:
                        pairs.append(reverse_pair)
        results = (Parallel(n_jobs=-1)(delayed(check_bonds)
                                       (pair[0], self.historical_data[pair[0]], pair[1], self.historical_data[pair[1]], self.rolling_window) for pair in pairs))
        results_frame = pd.DataFrame(results)
        results_frame.hedge_ratio = results_frame.hedge_ratio.astype(float)
        # drop the rows where complete_coint is false
        #results_frame = results_frame[results_frame.complete_coint]
        results_frame.sort_values(by=['score'], ascending=False, inplace=True)
        table = df_to_tt(results_frame)
        log.info(f'\n{table}')
        results = results_frame.iloc[0].copy()
        for bond in self.bonds_general_info:
            if bond.securityTerm == results.bond_1_name:
                bond_1_contract = bond.contract_details.contract
                conid1 = bond.contract_details.contract.conId
            if bond.securityTerm == results.bond_2_name:
                bond_2_contract = bond.contract_details.contract
                conid2 = bond.contract_details.contract.conId
        self.strategy_data = StrategyParameters(results.bond_1_name, results.bond_2_name, bond_1_contract, bond_2_contract, conid1,
                                                conid2, results.hedge_ratio, results.spread_mean, results.spread_std, results.time_to_revert, self.rolling_window)

    def get_bond_market_info(self):
        log.info('Connecting to Treasury Direct...')
        securities: Optional[list[USTreasurySecurity]] = get_bonds_info()
        if securities is None:
            log.info('Failed to get data from Treasury Direct...Aborting.')
            exit()
        self.bonds_general_info = securities
        rows: list[dict[str, str]] = []
        for security in securities:
            rows.append(security.summarize())
        df = pd.DataFrame(rows)
        table = df_to_tt(df)
        log.info(f'\n{table}')

    ### ------ Executions and Commissions -------###
    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        return super().execDetails(reqId, contract, execution)

    def commissionReport(self, commissionReport: CommissionReport):
        if self.trades:
            if len(self.trades[-1].commission_reports) < 4:
                self.trades[-1].commission_reports.append(commissionReport)
        return super().commissionReport(commissionReport)
