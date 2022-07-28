from ibapi.contract import Contract


def create_bond_contract_con_id(conID: str) -> Contract:
    """Assembles contract object for a bond from IBKR contract id number"""
    contract = Contract()
    contract.secType = 'BOND'
    contract.currency = 'USD'
    contract.exchange = 'SMART'
    contract.conId = conID
    return contract


def create_bond_contract_cusip(symbol: str) -> Contract:
    """Assembles contract object for a bond using cusip as a symbol"""
    contract = Contract()
    contract.secType = 'BOND'
    contract.currency = 'USD'
    contract.exchange = 'SMART'
    contract.symbol = symbol
    return contract
