from dataclasses import dataclass
from typing import Optional
from ibapi.order import Order
from ibapi.contract import Contract

@dataclass
class StrategyOrder:
    order: Optional[Order]
    contract: Optional[Contract]
    status: Optional[str]
    fill_price: Optional[float]
    sent_time: Optional[float]
    fill_time: Optional[float]

    @classmethod
    def create(cls, order: Order, contract: Contract) -> 'StrategyOrder':
        return cls(order=order, contract=contract, status='Unsent', fill_price=None, sent_time=None, fill_time=None)

    def is_filled(self) -> bool:
        return self.status == 'FILLED'

    def is_open(self) -> bool:
        open_order_statuses = ['Submitted',
                               'PendingSubmit', 'PendingCancel', 'PreSubmitted']
        return self.status in open_order_statuses

    def get_summary(self) -> dict:
        return {'account': self.order.account, 'action': self.order.action, 'quantity': self.order.totalQuantity, 'status': self.status, 'fill_price': self.fill_price, 'sent_time': self.sent_time, 'fill_time': self.fill_time, 'contract': self.contract.conId}
    
    def __eq__(self, __o: object) -> bool:
        return self.order.orderId == __o.order.orderId

    def __hash__(self) -> int:
        return hash(self.order.orderId)

def create_market_order(action: str, quantity: int, account: str) -> Order:
    """Assembles market order object"""
    # make sure action in ['BUY','SELL']
    if action not in ['BUY', 'SELL']:
        raise ValueError('action must be either BUY or SELL')
    order = Order()
    order.action = action
    order.account = account
    order.orderType = 'MKT'
    order.totalQuantity = abs(quantity)
    return order