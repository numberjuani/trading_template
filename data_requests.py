from dataclasses import dataclass
from enum import Enum
from typing import Optional
from ibapi.contract import Contract


class DataRequest(Enum):
    """Enum for data request types"""
    ContractInfo = 1,
    QuoteData = 2,
    MarketDepth = 3,
    TickData = 4,
    HistoricalData = 5,
    Positions = 6,
    Orders = 7,
    Account = 8,
    Executions = 9

    def __str__(self) -> str:
        return self.name


@dataclass
class Subscription:
    data_type: Optional[DataRequest]
    contract: Optional[Contract]
    name: str
    was_sent: bool = False
    send_time: Optional[float] = None

    def __eq__(self, other):
        if self.contract and other.contract:
            return self.contract.conId == other.contract.conId and self.data_type == other.data_type
        else:
            return self.data_type == other.data_type

    def __hash__(self):
        return hash((self.contract.conId, self.data_type))
