from ibapi.common import BarData
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PriceBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    wap: float
    bar_count: int

    @classmethod
    def from_bar_data(cls, bar_data: BarData) -> 'PriceBar':
        # yyyymmss hh:mm:ss
        timestamp = datetime.strptime(
            bar_data.date, '%Y%m%d %H:%M:%S')
        return cls(timestamp, bar_data.open, bar_data.high, bar_data.low, bar_data.close, bar_data.volume, bar_data.wap, bar_data.barCount)
