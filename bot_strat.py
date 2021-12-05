import MetaTrader5 as Mt5
from termcolor import colored
from typing import List, Optional, Union, Dict
import pandas as pd
from tools.market_data import return_datas
from tools.tools_trade import (
    positions_get,
    recup_all_symbol_conversion,
    close_one_trade_on_going,
)
from account import Account
from tools.candle import Candle
from random import choice
from trade import Trade
import schedule
import time
import yaml
from pathlib import Path

try:
    from personal_bot import live_trading_personnal_strat as live_trading_strat
except ImportError:
    live_trading_strat = live_trading_strat


__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


def bot_strategy(
        my_account: Optional[Account] = None,
        symbol: str = "EURUSD",
        account_currency: str = "USD",
        risk: float = 0.5,
        tf_list: list[int] = [Mt5.TIMEFRAME_M1],
        backtest_data: Optional[dict[str, pd.DataFrame]] = None,
        ema_list: Optional[List[int]] = [25, 50],
        bollinger_band: bool = False,
) -> Optional[dict[str, Union[bool, str, float, int]]]:
    """
    put your strat here
    """

    # NB1 : use Account class to pass attribute to the next iteration of this function (don't hesitate to create attribute inside init in Account class)
    # NB2 : Backtest only work with a unique TF for now. Works in progress
    DATA = return_datas(
        [symbol], tf_list, False, ema_list, backtest_data, bollinger_band
    )
    if backtest_data is None:
        symbol_broker_yaml = recup_all_symbol_conversion()
        account_currency_conversion = return_datas(
            symbol_broker_yaml["calcul_for_lot"], [Mt5.TIMEFRAME_M1], True
        )
        DATA_TF_1 = DATA[tf_list[0]][symbol]
    else:
        DATA_TF_1 = DATA[tf_list[0]]

    pips = 0.0001
    micro_pips = 0.00001
    last_candle_first_tf = Candle(DATA_TF_1.iloc[-1], ema_list=ema_list)

    # if you want your bot to trade only between 9H and 17H for (UTC+2)-PARIS but 8 and 16 on mt5)
    last_candle_hour = last_candle_first_tf.date.hour
    if last_candle_hour < 9 or last_candle_hour > 17:
        return None

    ########################
    ###### Manage bot ######
    ########################

    if backtest_data is None:
        trade_open = manage_bot(last_candle_first_tf, None)

    #######################
    ###### Bot strat ######
    #######################
    price = None
    size = None
    if last_candle_first_tf.close > last_candle_first_tf.emas[ema_list[0]]:
        sl = last_candle_first_tf.close - 3 * pips
        tp = last_candle_first_tf.close + 6 * pips
        order_type = Mt5.order_type_buy
    elif last_candle_first_tf.close < last_candle_first_tf.emas[ema_list[0]]:
        sl = last_candle_first_tf.close + 3 * pips
        tp = last_candle_first_tf.close - 6 * pips
        order_type = Mt5.order_type_sell
    else:
        return None
    comment = "my_bot_trade"
    ####################
    ### Taking trade ###
    ####################

    if backtest_data is None:
        if not trade_open:
            new_trade_is_open, result = take_trade(
                my_account,
                symbol,
                account_currency,
                order_type,
                risk,
                price,
                tp,
                sl,
                size,
                comment,
                account_currency_conversion,
            )
    else:
        if price is None:
            price = float(last_candle_first_tf.close)
        RR = float(abs(price - tp) / abs(price - sl))
        info_trade = {
            "order_type": order_type,
            "date_entry": str(last_candle_first_tf.date),
            "price": price,
            "RR": RR,
            "be": None,
            "tp": float(tp),
            "sl": float(sl),
            "pending": False,
            "on_going": True,
            "sl_to_be": False,
            "win": "On_going",
            "comment": comment,
        }
        return info_trade
    return None


def take_trade(
        my_account: Account,
        pair: str,
        account_currency: str,
        order_type: int,
        risk: float,
        price: Optional[float],
        tp: Optional[float],
        sl: Optional[float],
        size: Optional[float],
        comment: str,
        lot_all_pair: pd.DataFrame
):
    """
    create a new trade and open it
    """
    new_trade = Trade(
        pair,
        order_type,
        price=price,
        tp=tp,
        sl=sl,
        magic_number=545642,
        comment=comment,
    )
    new_trade_is_open, result = new_trade.open_position(
        my_account, account_currency, risk, lot_all_pair, size=size
    )
    return new_trade_is_open, result


def manage_bot(trade_info: Optional[Dict] = None):
    """
    manage on going trade

    If you are on backtest Mode and the STRAT_AUTO_MANAGE_TRADE (on backtest.py) is True,
    this function will be called by the backtest and you need to return 3 output :
    trade --> a dictionary with the new information of the trade (created in bot_strategy function in this file --> info_trade variable)
    trade_closing --> a bool to specified if the trade is closed
    result_trade  --> Optional[str] : None, "tp" or "sl".
    """

    if trade_info is not None:
        trade_closing = None
        result_trade = None
        return trade_info, trade_closing, result_trade
    else:
        all_trade_on_going = positions_get()
        for trade in all_trade_on_going.iloc():
            comment_trade = trade["comment"]
            if comment_trade != "my_bot_trade":
                continue
                # if you want to manage your trade you can close it here with some condition
                # trade_is_closed = close_one_trade_on_going(trade)
                # if trade_is_closed:
                #    print(colored(f"successfully closed trade : \n{trade}", "green"))
            return True
        return False


def live_trading(account_currency: str, risk: float, symbols: List[str]):
    """
    launch the bot every minute
    """
    if MY_PERSONNAL_BOT:
        live_trading_personnal_strat(account_currency, risk, symbols)
    else:
        my_account = Account(
            account_currency=account_currency,
            original_risk=risk,
        )
        my_account.connect(credential="demo_account_test.yaml")
        for symbol in symbols:
            (
                schedule.every(1).minutes.at(":01").do(
                    bot_strategy,
                    my_account,
                    symbol,
                    account_currency,
                    risk,
                )
            )
        while True:
            schedule.run_pending()
            time.sleep(1)
