import MetaTrader5 as mt5
from termcolor import colored
from typing import List, Optional, Union, Dict
import pandas as pd
from tools.market_data import return_datas
from tools.tools_trade import positions_get, take_trade, recup_all_symbol_conversion
from account import Account
from tools.candle import Candle
from random import choice
import schedule
from trade import Trade
import time
import yaml
from pathlib import Path


def bot_strategy(
    my_account: Optional[Account] = None,
    symbols: List[str] = ["EURUSD-Z"],
    account_currency: str = "USD",
    risk: float = 0.5,
    TF_list: list[int] = [mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M15],
    backtest_data: Optional[dict[str, pd.DataFrame]] = None,
    EMA_list: Optional[List[int]] = [25, 50],
    bollinger_band: bool = False,
) -> Optional[dict[str, Union[bool, str, float, int]]]:
    """
    put your strat here
    """

    # Backtest only work with an unique TF for now. Works in progress
    DATA = return_datas(
        symbols, TF_list, False, EMA_list, backtest_data, bollinger_band
    )
    if backtest_data is None:
        symbol_broker_yaml = recup_all_symbol_conversion()
        account_currency_conversion = return_datas(
            symbol_broker_yaml["calcul_for_lot"], [mt5.TIMEFRAME_M1], True
        )
    else:
        DATA_TF_1 = DATA[TF_list[0]]

    PIPS = 0.0001
    MICRO_PIPS = 0.00001

    LAST_CANDLE_FIRST_TF = Candle(DATA[TF_list[0]].iloc[-1], EMA_list = EMA_list)

    # if you want your bot to trade only between 9H and 17H for (UTC+2)-PARIS but 8 and 16 on mt5)
    last_candle_hour = LAST_CANDLE_FIRST_TF.date.hour
    if last_candle_hour < 9 or last_candle_hour > 17:
        return None

    #####################
    ### Bot strat #######
    #####################
    if price > LAST_CANDLE_FIRST_TF[f"EMA{EMA_list[0]}"] 
    order_type = mt5.ORDER_TYPE_SELL_LIMIT
    price = None
    tp = None
    sl = None
    size = None
    comment = "my bot trade"
    ####################
    ### Taking trade ###
    ####################

    if backtest_data is None:
        new_trade_is_open, result = take_trade(
            my_account,
            pair,
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
        info_trade = {
            "order_type": order_type,
            "date_entry": None,
            "price": float(price),
            "difference_sl_price": None,
            "difference_tp_price": None,
            "RR": None,
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





def live_trading(
    account_currency: str, risk: float, pair_list: List[str]
):
    """
    launch the bot every minute
    """
    my_account = Account(
        account_currency=account_currency,
        original_risk=risk,
    )
    my_account.connect(credential="your_credential.yaml")
    for pair in pair_list:
        schedule_object = (
            schedule.every(1)
            .minutes.at(":01")
            .do(
                bot_strategy,
                my_account,
                pair,
                account_currency,
                risk,
            )
        )
    while True:
        schedule.run_pending()
        time.sleep(1)
