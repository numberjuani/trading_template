import threading
import time
from pandas import read_json
from data_requests import DataRequest, Subscription
from strategy.pairs_trade import PairsTrade
from strategy.parameters import StrategyParameters
from strategy.status import StrategyStatus
from trading_app import TradingApp
from log_config import log
import configparser


def strategy_loop(app: TradingApp):
    while True:
        match app.status:
            case StrategyStatus.INITIALIZED:
                positions_timeout = False
                if app.seconds_since_start() > 6:
                    positions_timeout = True
                    log.info(
                        'No positions received for 5 seconds. Assuming flat.')
                if app.received_all_account_data(positions_timeout):
                    app.update_status(StrategyStatus.AWARE_OF_ACCOUNT)
            case StrategyStatus.AWARE_OF_ACCOUNT:
                if app.is_flat():
                    for bond in app.bonds_general_info:
                        contract = bond.to_ibkr_contract()
                        name = bond.securityTerm
                        contract_sub = Subscription(
                            DataRequest.ContractInfo, contract, name)
                        historical_sub = Subscription(
                            DataRequest.HistoricalData, contract, name)
                        if contract_sub not in app.requests:
                            app.requests[app.generate_req_id()] = contract_sub
                        if historical_sub not in app.requests:
                            app.requests[app.generate_req_id()
                                         ] = historical_sub
                    app.send_requests()
                    app.update_status(StrategyStatus.ANALYZING_PAIRS)
                else:
                    positions_table = app.produce_positions_table()
                    log.info(f'Positions \n{positions_table}')
                    app.strategy_data = StrategyParameters.from_pickle()
                    pair = PairsTrade.from_pickle_file()
                    if pair:
                        app.trades = [pair]
                    for position in app.positions.values():
                        quote_request = Subscription(
                            DataRequest.QuoteData, position.contract, position.name)
                        historical_request = Subscription(
                            DataRequest.HistoricalData, position.contract, position.name)
                        contract_sub = Subscription(
                            DataRequest.ContractInfo, position.contract, position.name)
                        if quote_request not in app.requests.values():
                            app.requests[app.generate_req_id()] = quote_request
                        if historical_request not in app.requests.values():
                            app.requests[app.generate_req_id()
                                         ] = historical_request
                        if contract_sub not in app.requests.values():
                            app.requests[app.generate_req_id()] = contract_sub
                        app.send_requests()
                    app.update_status(StrategyStatus.IN_A_TRADE)
            case StrategyStatus.ANALYZING_PAIRS:
                if app.has_data_to_analyze_pairs():
                    app.find_pairs_trade()
                    app.requests[app.generate_req_id()] = Subscription(
                        DataRequest.QuoteData, app.strategy_data.bond_1_contract, app.strategy_data.bond_1_name)
                    app.requests[app.generate_req_id()] = Subscription(
                        DataRequest.QuoteData, app.strategy_data.bond_2_contract, app.strategy_data.bond_2_name)
                    app.send_requests()
                    app.strategy_data.create_pickle_file()
                    app.update_status(StrategyStatus.WAITING_FOR_TRADES)
                else:
                    for bond in app.bonds_general_info:
                        contract = bond.to_ibkr_contract()
                        name = bond.securityTerm
                        contract_sub = Subscription(
                            DataRequest.ContractInfo, contract, name)
                        historical_sub = Subscription(
                            DataRequest.HistoricalData, contract, name)
                        if contract_sub not in app.requests.values():
                            app.requests[app.generate_req_id()] = contract_sub
                        if historical_sub not in app.requests.values():
                            app.requests[app.generate_req_id()
                                         ] = historical_sub
                    app.send_requests()
            case StrategyStatus.WAITING_FOR_TRADES:
                if app.has_data_to_place_trades():
                    band_ratio = 1
                    mid_price_spread = app.calculate_spread()
                    if mid_price_spread > app.strategy_data.spread_mean:
                        true_spread = app.calculate_true_spread(True)
                        if app.is_time_to_report():
                            log.info(
                                f'True price spread: {true_spread} low band {app.strategy_data.bottom_band(band_ratio)} top band {app.strategy_data.top_band(band_ratio)}')
                        if true_spread > app.strategy_data.top_band(band_ratio):
                            app.sell_the_spread()
                            app.update_status(
                                StrategyStatus.SENT_ENTRY_ORDERS)
                    else:
                        true_spread = app.calculate_true_spread(False)
                        if app.is_time_to_report():
                            log.info(
                                f'spread: {true_spread} low band {app.strategy_data.bottom_band(band_ratio)} top band {app.strategy_data.top_band(band_ratio)}')
                        if true_spread < app.strategy_data.bottom_band(band_ratio):
                            app.buy_the_spread()
                            app.update_status(StrategyStatus.SENT_ENTRY_ORDERS)
            case StrategyStatus.SENT_ENTRY_ORDERS:
                if app.trades:
                    if app.trades[-1].has_both_entries():
                        app.trades[-1].create_pickle_file()
                        app.update_status(StrategyStatus.IN_A_TRADE)
            case StrategyStatus.IN_A_TRADE:
                if app.has_data_to_calculate_unrealized_pnl() and app.has_data_to_calculate_spread():
                    spread = app.calculate_spread()
                    spread_reverted_to_mean = False
                    if app.previous_spread:
                        if (spread > app.strategy_data.spread_mean and app.previous_spread < app.strategy_data.spread_mean) or \
                                (spread < app.strategy_data.spread_mean and app.previous_spread > app.strategy_data.spread_mean):
                            spread_reverted_to_mean = True
                    ## check for trade closing conditions ##
                    if spread_reverted_to_mean:
                        if not app.has_open_orders():
                            app.close_all_positions()
                            log.info(
                                'Spread has reverted to the mean. Closing all positions')
                        app.update_status(StrategyStatus.SENT_EXIT_ORDERS)
                    ##periodic update##
                    if app.is_time_to_report():
                        tt = app.get_positions_table()
                        log.info(f'\n{tt}')
                        ##end periodic update##
                    app.previous_spread = spread
            case StrategyStatus.SENT_EXIT_ORDERS:
                if app.trades[-1].is_complete():
                    report = app.trades[-1].report()
                    log.info(f'Trade Closed. Net PnL: {report}')
                    app.trades[-1].delete_pickle_file()
                    app.strategy_data.delete_pickle_file()
                    app.update_status(StrategyStatus.ANALYZING_PAIRS)


def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    account = config.get('trading', 'account')
    percent_of_account_to_use = config.getfloat(
        'trading', 'percent_of_account_to_use')
    rolling_window = config.getint('trading', 'rolling_window')
    bar_interval = config.getint('trading', 'bar_interval')
    rolling_window = config.getint('trading', 'rolling_window')
    server_name = config.get('server', 'name')
    server_type = config.get('server', 'type')
    log.info('Starting...')
    app = TradingApp(account, bar_interval, rolling_window,
                     percent_of_account_to_use)
    app.get_bond_market_info()
    app.requests[app.generate_req_id()] = Subscription(
        DataRequest.Positions, None, 'Positions', False)
    app.requests[app.generate_req_id()] = Subscription(
        DataRequest.Account, None, 'Account', False)
    app.requests[app.generate_req_id()] = Subscription(
        DataRequest.Orders, None, 'Account', False)
    ports = read_json('ibkr-ports.json')
    log.info('Connecting to Interactive Brokers...')
    app.connect('127.0.0.1', ports[server_name][server_type], clientId=0)
    time.sleep(0.1)
    if not app.isConnected():
        log.error('Failed to connect to Interactive Brokers')
        exit()
    else:
        log.info('Connected to Interactive Brokers')
    app.send_requests()
    strategy_thread = threading.Thread(
        target=strategy_loop, args=(app,), daemon=True)
    strategy_thread.start()
    app.run()


if __name__ == "__main__":
    main()
