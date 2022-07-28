from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from market_data.historical import PriceBar
from others import create_pickle_file, delete_file,read_pickle_file
from statsmodels.api import OLS
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from strategy.orders import StrategyOrder
from ibapi.commission_report import CommissionReport

@dataclass
class PairsTrade:
    entry_orders:list[StrategyOrder]
    exit_orders:list[StrategyOrder]
    gross_pnl: Optional[float]
    commission_reports: list[CommissionReport] 

    _FILENAME: str = 'pairs_trade.pickle'

    @classmethod
    def open(cls, entry_order:StrategyOrder) -> 'PairsTrade':
        """Starts the class from a single trade entry"""
        return PairsTrade([entry_order], [], None,[])

    @classmethod
    def from_pickle_file(cls) -> Optional['PairsTrade']:
        return read_pickle_file(cls._FILENAME)
    
    def create_pickle_file(self) -> None:
        create_pickle_file(self,self._FILENAME)
    
    def delete_pickle_file(self):
        delete_file(self._FILENAME)

    def add_exit_order(self, other_order:StrategyOrder) -> None:
        if self.exit_orders:
            if len(self.exit_orders) < 2:
                if self.exit_orders[0] != other_order:
                    self.exit_orders.append(other_order)
        else:
            self.exit_orders.append(other_order)

    def add_entry_order(self, other_order:StrategyOrder) -> None:
        if self.entry_orders:
            if len(self.entry_orders) < 2:
                if self.entry_orders[0] != other_order:
                    self.entry_orders.append(other_order)
        else:
            self.entry_orders.append(other_order)

    def is_complete(self) -> bool:
        return len(self.entry_orders) == 2 and len(self.exit_orders) == 2

    def has_both_entries(self) -> bool:
        return len(self.entry_orders) == 2

    def calculate_gross_pnl(self) -> Optional[float]:
        if self.is_complete():
            contracts = [order.contract for order in self.exit_orders]
            gross_pnl = 0.0
            for contract in contracts:
                for order in self.entry_orders:
                    if order.contract.conId == contract.conId:
                        entry_order = order
                for order in self.exit_orders:
                    if order.contract.conId == contract.conId:
                        exit_order = order
                if entry_order.order.action == 'BUY':
                    gross_pnl += float(exit_order.order.totalQuantity) *(
                        float(exit_order.fill_price) - float(entry_order.fill_price))
                elif entry_order.order.action == 'SELL':
                    gross_pnl += -float(exit_order.order.totalQuantity) *(
                        float(exit_order.fill_price) - float(entry_order.fill_price))
            return gross_pnl
        else:
            return None

    def calculate_total_commissions(self) -> float:
        commissions = 0.0
        for report in self.commission_reports:
            commissions += report.commission
        return commissions

    def report(self) -> dict:
        realized_pnl_sum = self.commission_reports[2].realizedPNL + self.commission_reports[3].realizedPNL
        gross = self.calculate_gross_pnl()
        if gross and self.entry_orders[0].contract.secType == 'BOND':
            gross = round(10*gross,2)
        total_commissions = round(self.calculate_total_commissions(),2)
        if gross:
            net = round(gross - total_commissions,2)
            return {'gross pnl': gross, 'net pnl': net, 'total_commissions': total_commissions, 'executions': realized_pnl_sum}
        else:
            return {}

def is_cointegrated_simple(spread: pd.Series):
    """Checks for cointegration of two series without a data split"""
    adf_results = adfuller(spread)
    if adf_results[0] <= adf_results[4]['10%']:
        return (True, adf_results[0])
    else:
        return (False, adf_results[0])

def is_cointegrated(x, y):
    """Checks for cointegration of two series with a data split"""
    assert len(x) == len(y)
    half = int(0.5*len(x))
    result = OLS(x.iloc[:half], y.iloc[:half]).fit()
    hedge_ratio = round(result.params[0],2)
    spread = x - hedge_ratio*y
    adf_results = adfuller(spread[half:])
    if adf_results[0] <= adf_results[4]['10%']:
        return (True, hedge_ratio)
    else:
        return (False, hedge_ratio)

def calculate_realtime_hedge_ratio(x, y) -> float:
    assert len(x) == len(y)
    result = OLS(x, y).fit()
    hedge_ratio = result.params[0]
    return hedge_ratio

def calculate_time_to_revert(data):
    result = coint_johansen(data, 0, 1)
    theta = result.eig[0]
    half_life = round(np.log(2) / theta, 2)
    return half_life

def check_bonds(bond_1_name: str, bond_1_data: list[PriceBar], bond_2_name: str, bond_2_data: list[PriceBar], rolling_window: int):
    bond_1_data = pd.DataFrame([x.__dict__ for x in bond_1_data])
    bond_2_data = pd.DataFrame([x.__dict__ for x in bond_2_data])
    bond_1_data.set_index('timestamp', inplace=True)
    bond_2_data.set_index('timestamp', inplace=True)
    both = pd.merge(bond_1_data, bond_2_data, how='inner',
                    left_index=True, right_index=True, suffixes=('_1', '_2'))
    both['rolling_corr'] = both['close_1'].rolling(window=rolling_window).corr(both['close_2'])
    complete_coint, hedge_ratio = is_cointegrated(both['close_1'], both['close_2'])
    spread = both['close_1'] - hedge_ratio*both['close_2']
    spread_mean = round(spread.rolling(window=rolling_window).mean()[-1],2)
    spread_std = round(spread.rolling(window=rolling_window).std()[-1],2)
    time_to_revert = calculate_time_to_revert(
        both[['close_1', 'close_2']])
    top_band = round(spread_mean + spread_std, 4)
    bottom_band = round(spread_mean - spread_std, 4)
    corr_mean = 100*round(both['rolling_corr'].mean(), 4)
    score = round((corr_mean * spread_std)/time_to_revert, 4)
    return_dict =  {'bond_1_name': bond_1_name, 'hedge_ratio': hedge_ratio, 'bond_2_name': bond_2_name, 'complete_coint': complete_coint, 'corr_mean': int(corr_mean),
            'time_to_revert': time_to_revert, 'spread_mean': spread_mean, 'spread_std': spread_std, 'score': score, 'top_band': top_band, 'bottom_band': bottom_band}
    #print(return_dict)
    return return_dict
