from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Quote:
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    mid_price: Optional[float] = None
    last_update_time: Optional[float] = None

    @classmethod
    def from_tick(cls, tickType: int, value: float) -> 'Quote':
        q = cls()
        q.update_quote(tickType, value)
        return q

    def update_quote(self, tickType: int, value: float):
        self.last_update_time = datetime.now().timestamp()
        match tickType:
            case 0:
                self.bid_size = value
            case 1:
                self.bid_price = value
            case 2:
                self.ask_price = value
            case 3:
                self.ask_size = value
        if self.ask_price != None and self.bid_price != None:
            self.mid_price = (self.ask_price + self.bid_price)/2

    def is_valid(self, acceptable_delay: float) -> bool:
        """Checks that all the fields are present and it was updates within the last acceptable_delay seconds"""
        all_data = self.bid_price and self.ask_price and self.bid_size and self.ask_size and self.mid_price
        fresh = (datetime.now().timestamp() -
                 self.last_update_time) <= acceptable_delay
        return all_data and fresh
