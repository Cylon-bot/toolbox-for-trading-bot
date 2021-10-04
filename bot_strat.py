import MetaTrader5 as mt5
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
    from personnal_bot import live_trading_personnal_strat

    MY_PERSONNAL_BOT = True
except:
    MY_PERSONNAL_BOT = False


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
    TF_list: list[int] = [mt5.TIMEFRAME_M1],
    backtest_data: Optional[dict[str, pd.DataFrame]] = None,
    EMA_list: Optional[List[int]] = [25, 50],
    bollinger_band: bool = False,
) -> Optional[dict[str, Union[bool, str, float, int]]]:
    """
    put your strat here
    """

    # NB1 : use Account class to pass attribute to the next iteration of this function (don't hesitate to create attribute inside init in Account class)
    # NB2 : Backtest only work with a unique TF for now. Works in progress
    DATA = return_datas(
        [symbol], TF_list, False, EMA_list, backtest_data, bollinger_band
    )
    if backtest_data is None:
        symbol_broker_yaml = recup_all_symbol_conversion()
        account_currency_conversion = return_datas(
            symbol_broker_yaml["calcul_for_lot"], [mt5.TIMEFRAME_M1], True
        )
        DATA_TF_1 = DATA[TF_list[0]][symbol]
    else:
        DATA_TF_1 = DATA[TF_list[0]]

    PIPS = 0.0001
    MICRO_PIPS = 0.00001
    LAST_CANDLE_FIRST_TF = Candle(DATA_TF_1.iloc[-1], EMA_list=EMA_list)

    # if you want your bot to trade only between 9H and 17H for (UTC+2)-PARIS but 8 and 16 on mt5)
    last_candle_hour = LAST_CANDLE_FIRST_TF.date.hour
    if last_candle_hour < 9 or last_candle_hour > 17:
        return None

    ########################
    ###### Manage bot ######
    ########################

    if backtest_data is None:
        trade_open = manage_bot(LAST_CANDLE_FIRST_TF, None)

    #######################
    ###### Bot strat ######
    #######################
    price = None
    size = None
    if LAST_CANDLE_FIRST_TF.close > LAST_CANDLE_FIRST_TF.EMAs[EMA_list[0]]:
        sl = LAST_CANDLE_FIRST_TF.close - 3 * PIPS
        tp = LAST_CANDLE_FIRST_TF.close + 6 * PIPS
        order_type = mt5.ORDER_TYPE_BUY
    elif LAST_CANDLE_FIRST_TF.close < LAST_CANDLE_FIRST_TF.EMAs[EMA_list[0]]:
        sl = LAST_CANDLE_FIRST_TF.close + 3 * PIPS
        tp = LAST_CANDLE_FIRST_TF.close - 6 * PIPS
        order_type = mt5.ORDER_TYPE_SELL
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
            price = float(LAST_CANDLE_FIRST_TF.close)
        RR = float(abs(price - tp) / abs(price - sl))
        info_trade = {
            "order_type": order_type,
            "date_entry": str(LAST_CANDLE_FIRST_TF.date),
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
    lot_all_pair: pd.DataFrame,
) -> (bool, "MqlTradeRequest"):
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


def manage_bot(LAST_CANDLE: Candle, trade_info: Optional[Dict] = None):
    """
    manage on going trade 

    If you are on backtest Mode and the STRAT_AUTO_MANAGE_TRADE (on backtest.py) is True,
    this function will be called by the backtest and you need to return 3 output :
    trade --> a dictionnary with the new informations of the trade (created in bot_strategy function in this file --> info_trade variable)
    trade_closing --> a bool to specified if the trade is closed
    result_trade  --> Optional[str] : None, "tp" or "sl".
    """

    if trade_info is not None :
        trade_closing = None
        result_trade = None
        return trade_info, trade_closing, result_trade
    else :
        all_trade_on_going = positions_get()
        for trade in all_trade_on_going.iloc():
            comment_trade = trade["comment"]
            if comment_trade != "my_bot_trade":
                continue
                # if you want to manage your trade you can close it here with some condition
                # trade_is_closed = close_one_trade_on_going(trade)
                # if trade_is_closed:
                #    print(colored(f"succesfully closed trade : \n{trade}", "green"))
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
            schedule_object = (
                schedule.every(1)
                .minutes.at(":01")
                .do(
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
