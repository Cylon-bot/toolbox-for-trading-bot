import pytz
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
import sys
from typing import Dict, List, Optional
from copy import deepcopy
from account import Account
import yaml
from pathlib import Path
from termcolor import colored

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


def calc_lot_forex(
    risk: float,
    symbol: str,
    sl: float,
    balance: float,
    account_currency_conversion: float,
):
    """
    calc lot size for forex
    """
    PERCENTAGE_CONVERTER = 0.01
    RISK_PERCENTAGE = risk * PERCENTAGE_CONVERTER
    CURRENCY_2 = symbol[3:6]
    if CURRENCY_2 == "JPY":
        JPY_PIP_CONVERTER = 100
        PIP_VALUE = (balance * RISK_PERCENTAGE) / (sl * JPY_PIP_CONVERTER)
    else:
        PIP_VALUE = (balance * RISK_PERCENTAGE) / sl
    ONE_LOT_PRICE = 100_000
    lot_calcul = (PIP_VALUE / ONE_LOT_PRICE) * (account_currency_conversion)
    lot_size = round(lot_calcul, 2)
    return lot_size


def calc_account_currency_conversion(
    account_currency: str, symbol: str, current_price_symbols: Dict
):
    """
    calculate the price conversion between the traded symbol and your account currency
    """
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
                print(
                    f"unable to find a lot for {CURRENCY_2 + account_currency + OTHER_CHARACTER}"
                )
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
    account_currency_conversion = calc_account_currency_conversion(
        account_currency, symbol, current_price_symbols
    )
    lot_size = calc_lot_forex(risk, symbol, sl, BALANCE, account_currency_conversion)
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


def recup_all_symbol_conversion(
    path_symbol_broker: str = "symbol_broker.yaml",
) -> Dict[str, List[str]]:
    ABSOLUTE_PATH_LAUNCH = Path.cwd()
    SYMBOL_BROKER_PATH = ABSOLUTE_PATH_LAUNCH / path_symbol_broker
    with open(SYMBOL_BROKER_PATH) as symbol_broker_file:
        symbol_broker_yaml = yaml.load(symbol_broker_file, Loader=yaml.FullLoader)
    return symbol_broker_yaml


def close_one_trade_on_going(trade: pd.Series):
    if (
        trade["type"] == mt5.ORDER_TYPE_BUY
        or trade["type"] == mt5.ORDER_TYPE_BUY_STOP
        or trade["type"] == mt5.ORDER_TYPE_BUY_LIMIT
    ):
        order_type_close = mt5.ORDER_TYPE_SELL
        price_close = mt5.symbol_info_tick(trade["symbol"]).bid
    elif (
        trade["type"] == mt5.ORDER_TYPE_SELL
        or trade["type"] == mt5.ORDER_TYPE_SELL_STOP
        or trade["type"] == mt5.ORDER_TYPE_SELL_LIMIT
    ):
        order_type_close = mt5.ORDER_TYPE_BUY
        price_close = mt5.symbol_info_tick(trade["symbol"]).ask
    volume_to_close = float(trade["volume"])
    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": trade["symbol"],
        "volume": volume_to_close,
        "type": order_type_close,
        "position": int(trade["ticket"]),
        "price": price_close,
        "magic": 5430,
        "deviation": 50,
        "comment": f"Close from robot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result_close_request = mt5.order_send(close_request)
    while result_close_request.comment == "Requote":
        if order_type_close == mt5.ORDER_TYPE_BUY:
            price_close = mt5.symbol_info_tick(trade["symbol"]).ask
            close_request["price"] = price_close
        elif order_type_close == mt5.ORDER_TYPE_SELL:
            price_close = mt5.symbol_info_tick(trade["symbol"]).bid
            close_request["price"] = price_close
        result_close_request = mt5.order_send(close_request)

    if result_close_request.retcode != mt5.TRADE_RETCODE_DONE:
        print(result_close_request)
        print("Failed to close order :(")
        return False
    else:
        print("Order successfully closed!")
        return True


def move_sl_to_be(trade, decal_sl_be: float):
    stop_loss_trade = trade.sl
    entering_price = trade.price_open
    take_profit_trade = trade.tp
    symbol = trade.symbol
    ticket = trade.ticket
    trade_comment = trade.comment
    trade_order_type = trade.type
    if (
        trade_order_type == mt5.ORDER_TYPE_SELL_LIMIT
        or trade_order_type == mt5.ORDER_TYPE_SELL
        or trade_order_type == mt5.ORDER_TYPE_SELL_STOP
    ):
        decal_sl_be = -decal_sl_be

    if float(stop_loss_trade) != float(entering_price + decal_sl_be):
        modify_request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "sl": entering_price + decal_sl_be,
            "position": int(ticket),
            "tp": take_profit_trade,
            "comment": trade_comment,
        }
        result_modify_request = mt5.order_send(modify_request)
        if result_modify_request.retcode != mt5.TRADE_RETCODE_DONE:
            print(
                f"Failed to modify order :(, retcode: {result_modify_request.retcode}"
            )
            print(colored(result_modify_request, "blue"))
        else:
            print(colored(f"\n{'-'*100}\n", "blue"))
            print(colored(f"succesfully place SL to BE for trade :", "green"))

            for key, value in trade.to_dict().items():
                print(colored(f"{key} : {value}", "green"))
    else:
        pass
