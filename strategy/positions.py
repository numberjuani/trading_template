from dataclasses import dataclass
from ibapi.contract import Contract
from ibapi.order import Order
from typing import Optional
from market_data.quotes import Quote
from strategy.orders import create_market_order

@dataclass
class StrategyPosition:
    contract: Contract
    name: str
    cusip: str
    account: str
    average_price: float
    quantity: int
    closing_order_sent: bool = False

    @classmethod
    def from_filled_order(cls, order: Order, contract: Contract, avg_price: float,name:str,cusip:str) -> 'StrategyPosition':
        return cls(contract=contract, account=order.account, average_price=avg_price, quantity=order.totalQuantity,name=name,cusip=cusip)

    def unrealized_pnl(self, quote: Quote) -> Optional[float]:
        if quote.is_valid(5.0):
            price = quote.bid_price if self.quantity > 0 else quote.ask_price
            pnl = float(self.quantity) * (float(price) - float(self.average_price))
            if self.contract.secType == 'BOND':
                pnl *= 10
            return pnl
        else:
            return None

    def create_closing_order(self) -> Order:
        order = Order()
        order.account = self.account
        if self.quantity > 0:
            order = create_market_order('SELL', self.quantity, self.account)
        elif self.quantity < 0:
            order = create_market_order('BUY', self.quantity, self.account)
        return order

    def to_row(self) -> dict:
        return {'contract': self.contract.conId, 'cusip':self.cusip,'name':self.name,'account': self.account, 'average_price': self.average_price, 'quantity': self.quantity}

    def to_row_with_unrealized_pnl(self, quote:Quote) -> dict:
        pnl = round(self.unrealized_pnl(quote),2)
        return {'cusip':self.cusip,'contract': self.contract.conId,'term':self.name,'account': self.account, 'average_price': round(self.average_price,2), 'quantity': self.quantity,'bid price':quote.bid_price,'ask_price':quote.ask_price, 'unrealized_pnl': pnl}
