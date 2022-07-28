import json
import pickle
from colorama import Fore
from prettytable import PrettyTable
import pandas as pd
from typing import Optional
import datetime as dt
import os
from log_config import log

def df_to_tt(dataframe: pd.DataFrame) -> PrettyTable:
    """Transforms pandas dataframe to terminal table"""
    x = PrettyTable()
    x.field_names = list(dataframe.columns)
    for _, row in dataframe.iterrows():
        x.add_row(list(row))
    return x


def create_json_file(filepath: str, data: dict):
    """Creates a json file"""
    with open(filepath, 'w') as f:
        json.dump(data, f)
        f.close()


def read_json_file(filepath: str) -> Optional[dict]:
    """This function reads a json file or throws an error if the file is not found"""
    try:
        with open(filepath, 'r') as f:
            log.info(f'Success Reading json file: {filepath}')
            data = json.load(f)
            f.close()
    except FileNotFoundError:
        log.error(f'Strategy File not found: {filepath}')
        data = None
    return data


def estimate_bond_name(last_trading_date: dt.date) -> str:
    """Estimates the likely bond security term using the days to expiration"""
    days_to_last_trading_date = (
        last_trading_date - dt.datetime.today().date()).days
    twenty_years = 365 * 20
    ten_years = 365 * 10
    five_years = 365 * 5
    two_years = 365 * 2
    if days_to_last_trading_date > twenty_years:
        return '30-year'
    elif days_to_last_trading_date > ten_years:
        return '20-year'
    elif days_to_last_trading_date > five_years:
        return '10-year'
    elif days_to_last_trading_date > two_years:
        return '5-year'
    else:
        return '2-year'


def delete_file(filepath: str):
    """Deletes a file"""
    try:
        with open(filepath, 'r') as f:
            f.close()
        os.remove(filepath)
    except FileNotFoundError:
        log.error(f'File not found: {filepath}')


def create_pickle_file(obj: object, filename: str) -> None:
    try:
        with open(filename, 'wb') as f:
            pickle.dump(obj, f)
    except Exception as e:
        log.error(f'Error creating pickle file: {filename}')


def read_pickle_file(filename: str) -> Optional[object]:
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
    except Exception as e:
        log.error(f'Error reading pickle file: {filename}')
        data = None
    return data
