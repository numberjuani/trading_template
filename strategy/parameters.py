from dataclasses import dataclass
from typing import Optional
from ibapi.contract import Contract
from others import create_pickle_file, delete_file, read_pickle_file

@dataclass
class StrategyParameters:
    bond_1_name: str
    bond_2_name: str
    bond_1_contract: Optional[Contract]
    bond_2_contract: Optional[Contract]
    bond_1_contract_id: int
    bond_2_contract_id: int
    hedge_ratio: float
    spread_mean: float
    spread_std: float
    time_to_revert: float
    rolling_window: int

    _FILENAME: str = 'strategy_params.pickle'

    @classmethod
    def from_pickle(cls) -> Optional['StrategyParameters']:
        return read_pickle_file(cls._FILENAME)

    def create_pickle_file(self):
        create_pickle_file(self, self._FILENAME)

    def top_band(self,ratio:float=1.0) -> float:
        return round(self.spread_mean + ratio*self.spread_std, 4)

    def bottom_band(self,ratio:float=1.0) -> float:
        return round(self.spread_mean - ratio*self.spread_std, 4)
    
    def delete_pickle_file(self):
        delete_file(self._FILENAME)
        return



