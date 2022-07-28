from enum import Enum

class StrategyStatus(Enum):
    # means only that the program has started, is unaware of market, account, positions, and strategy
    INITIALIZED = 1
    # means that the strategy is now aware of positions and balance in the account, can decide where to go
    AWARE_OF_ACCOUNT = 2
    # means no trades are open, so it will analyze all bond pairs looking for trades
    ANALYZING_PAIRS = 3
    # a pairs has been found and is now waiting for the spread to widen
    WAITING_FOR_TRADES = 4
    # entry orders were sent
    SENT_ENTRY_ORDERS = 5
    # an active trade is ongoing
    IN_A_TRADE = 6
    # orders to exit were sent
    SENT_EXIT_ORDERS = 7

    def __str__(self):
        return self.name









    