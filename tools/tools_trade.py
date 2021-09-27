import pytz
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
import sys
from typing import Dict, List
from copy import deepcopy
from account import Account

######################################
##### THIS FILE NEED REFACTORING #####
######################################


def calc_position_size_index(
    symbol: str,
    account_currency: str,
    risk: float,
    sl: int,
    last_row_lot_all_pair: dict,
    account: Account,
    list_index_eu: List[str] = [],
    list_index_us: List[str] = [],
    list_index_gb: List[str] = [],
) -> float:
    """
    calculte lot size for index order
    """
    ACCOUNT = mt5.account_info()
    BALANCE = ACCOUNT.balance
    SL_PIPS = sl / 100000
    PERCENTAGE_CONVERTER = 0.01
    RISK_PERCENTAGE = risk * PERCENTAGE_CONVERTER
    PIP_VALUE = (BALANCE * RISK_PERCENTAGE) / SL_PIPS
    PRICE_CFD = 1
    if symbol in list_index_eu:
        if account_currency != "EUR":
            if account.normal_account:
                SYMBOL_TO_CONVERT = "EURUSD"
            else:
                SYMBOL_TO_CONVERT = "EURUSD-Z"
            close_candle_symbol_to_convert = 1 / float(
                last_row_lot_all_pair[SYMBOL_TO_CONVERT]["close"]
            )

            CONVERSION_COTATION = PRICE_CFD / close_candle_symbol_to_convert
        else:
            CONVERSION_COTATION = 1

        lot_size_index_eu = PIP_VALUE / CONVERSION_COTATION
        lot_size_index_eu = round(lot_size_index_eu, 1)
        return lot_size_index_eu
    elif symbol in list_index_us:
        if account_currency != "USD":
            if account.normal_account:
                SYMBOL_TO_CONVERT = "EURUSD"
            else:
                SYMBOL_TO_CONVERT = "EURUSD-Z"
            close_candle_symbol_to_convert = float(
                last_row_lot_all_pair[SYMBOL_TO_CONVERT]["close"]
            )

            CONVERSION_COTATION = PRICE_CFD / close_candle_symbol_to_convert
        else:
            CONVERSION_COTATION = 1
        lot_size_index_us = PIP_VALUE / CONVERSION_COTATION
        lot_size_index_us = round(lot_size_index_us, 1)
        return lot_size_index_us
    elif symbol in list_index_gb:
        if account_currency != "GBP":
            if account_currency == "USD":
                if account.normal_account:
                    SYMBOL_TO_CONVERT = "GBP" + account_currency
                else:
                    SYMBOL_TO_CONVERT = "GBP" + account_currency + "-Z"

                close_candle_symbol_to_convert = 1 / float(
                    last_row_lot_all_pair[SYMBOL_TO_CONVERT]["close"]
                )
            else:
                if account_currency == "USD":
                    SYMBOL_TO_CONVERT = account_currency + "GBP"
                else:
                    SYMBOL_TO_CONVERT = account_currency + "GBP" + "-Z"
                close_candle_symbol_to_convert = float(
                    last_row_lot_all_pair[SYMBOL_TO_CONVERT]["close"]
                )

            CONVERSION_COTATION = PRICE_CFD / close_candle_symbol_to_convert
        else:
            CONVERSION_COTATION = 1
        lot_size_index_gb = PIP_VALUE / CONVERSION_COTATION
        lot_size_index_gb = round(lot_size_index_gb, 1)
        return lot_size_index_gb


def calc_lot_forex(risk: float, currency_2: str, sl: float, balance: float, price_conversion_symbol_to_account_currency: float) :
    '''
        calc lot size for forex 
    '''
    PERCENTAGE_CONVERTER = 0.01
    RISK_PERCENTAGE = risk * PERCENTAGE_CONVERTER
    if currency_2 == "JPY":
        JPY_PIP_CONVERTER = 100
        PIP_VALUE = (balance * RISK_PERCENTAGE) / (sl*JPY_PIP_CONVERTER)
    else :
        PIP_VALUE = (balance * RISK_PERCENTAGE) / sl
    ONE_LOT_PRICE = 100_000
    lot_calcul = (PIP_VALUE/ONE_LOT_PRICE)*(price_conversion_symbol_to_account_currency)
    lot_size = round(lot_size, 2)
    return lot_size

def calc_account_currency_conversion(account_currency: str, symbol: str, current_price_symbols: Dict) :
    '''
        calculate the price conversion between the traded symbol and your account currency
    '''
    CURRENCY_2 = symbol[3:6]
    OTHER_CHARACTER = symbol[6:]
    if account_currency == CURRENCY_2:
        account_currency_conversion = 1
    else:
        symbol_to_convert = account_currency + CURRENCY_2 + OTHER_CHARACTER
        symbol_is_real = check_symbol(symbol_to_convert)
        if symbol_is_real:
            account_currency_conversion = float(
                current_price_symbols[symbol_to_convert]["close"]
            )
        else:
            symbol_to_convert = CURRENCY_2 + account_currency + OTHER_CHARACTER
            symbol_is_real = check_symbol(symbol_to_convert)
            if symbol_is_real:
                account_currency_conversion = 1 / float(
                    current_price_symbols[symbol_to_convert]["close"]
                )
            else:
                print(f"unable to find a lot for {CURRENCY_2 + account_currency + OTHER_CHARACTER}")
                return None
    return account_currency_conversion
    
def calc_position_size_forex(
    symbol: str,
    account_currency: str,
    risk: float,
    sl: float,
    current_price_symbols: dict,
    account: Account,
) -> Optional[float]:
    """
        return lot size for forex
    """
    ACCOUNT = mt5.account_info()
    BALANCE = ACCOUNT.balance
    account_currency_conversion = calc_account_currency_conversion(account_currency, symbol, current_price_symbols)
    lot_size = calc_lot_forex(risk, CURRENCY_2, sl, BALANCE, account_currency_conversion)
    return lot_size


def get_order_history(
    date_from: datetime = datetime.now() - timedelta(hours=24),
    date_to: datetime = datetime.now() + timedelta(hours=5),
):
    """
    get history of trades from the connected account
    """
    res = mt5.history_deals_get(date_from, date_to)
    if res is not None and res != ():
        df = pd.DataFrame(list(res), columns=res[0]._asdict().keys())
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    return pd.DataFrame()


def calc_daily_lost_trades():
    """
    calculate the daily lost trades
    """
    now = datetime.now().astimezone(pytz.timezone("Etc/GMT-3"))
    now = datetime(now.year, now.month, now.day, hour=now.hour, minute=now.minute)
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    res = get_order_history(midnight, now)

    if res.empty:
        return 0
    else:
        lost_trade_count = 0
        for i, row in res.iterrows():
            profit = float(row["profit"])
            if profit < 0:
                lost_trade_count = lost_trade_count + 1
        return lost_trade_count


def get_daily_trade_data() -> "history_order":
    """
    calculate the daily lost trades
    """
    now = datetime.now().astimezone(pytz.timezone("Etc/GMT-3"))
    now = datetime(now.year, now.month, now.day, hour=now.hour, minute=now.minute)
    yesterday = now - timedelta(hours=24)
    res = get_order_history(yesterday, now)
    return res


def check_max_drawdown(
    initial_balance: float, current_balance: float, max_drawdown: float
) -> bool:
    """
    check if the loss exceed the max given drawdown
    """
    PERCENTAGE = 0.01
    MAX_DRAWDOWN_PERCENTAGE = max_drawdown * PERCENTAGE
    is_in_drawdown = False
    if current_balance < (initial_balance - initial_balance * MAX_DRAWDOWN_PERCENTAGE):
        is_in_drawdown = True

    return is_in_drawdown


def positions_get(symbol=None) -> pd.DataFrame:
    """
    return all on going positions
    """
    if symbol is None:
        res = mt5.positions_get()
    else:
        res = mt5.positions_get(symbol=symbol)
    if res is not None and res != ():
        df = pd.DataFrame(list(res), columns=res[0]._asdict().keys())
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    return pd.DataFrame()


def closing_all_pending_order(my_account: Account):
    """
    close all pending order
    """
    pending_trade_dict = deepcopy(my_account.trade_pending)
    for ticket_order, trade_pending in pending_trade_dict.items():
        trade_pending.close_position(my_account)


def closing_all_on_going_order(my_account: Account):
    """
    close all on going order
    """
    on_going_trade_dict = deepcopy(my_account.trade_on_going)
    for ticket_order, trade_on_going in on_going_trade_dict.items():
        trade_on_going.close_position(my_account)


def check_symbol(pair: str):
    """
    check if the symbol given by the user exist in the broker trading list
    """
    symbol_info = mt5.symbol_info(pair)
    if symbol_info is None:
        return False

    if not symbol_info.visible:
        if not mt5.symbol_select(pair, True):
            return False
    return True
