import MetaTrader5 as mt5
from termcolor import colored
from typing import List, Optional, Union, Dict, Tuple
import pandas as pd
from tools.market_data import return_datas
from tools.tools_trade import (
    positions_get,
    recup_all_symbol_conversion,
    close_one_trade_on_going,
    move_sl_to_be,
)
from account import Account
from tools.candle import Candle
from random import choice
from trade import Trade
import schedule
import time
import yaml
from pathlib import Path

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


def my_personal_bot_strategy(
    my_account: Optional[Account] = None,
    symbol: str = "EURUSD-Z",
    account_currency: str = "USD",
    risk: float = 0.25,
    TF_list: list[int] = [mt5.TIMEFRAME_M1],
    backtest_data: Optional[dict[str, pd.DataFrame]] = None,
    EMA_list: Optional[List[int]] = None,
    bollinger_band: bool = True,
    RSI: bool = True,
    interval_hour: Tuple[int] = (9, 18),
) -> Optional[dict[str, Union[bool, str, float, int]]]:
    """
    put your strat here
    """

    # NB1 : use Account class to pass attribute to the next iteration of this function (don't hesitate to create attribute inside init in Account class)
    # NB2 : Backtest only work with a unique TF for now. Works in progress
    DATA = return_datas(
        [symbol], TF_list, False, EMA_list, backtest_data, bollinger_band, RSI
    )
    if backtest_data is None:
        symbol_broker_yaml = recup_all_symbol_conversion()
        account_currency_conversion = return_datas(
            symbol_broker_yaml["calcul_for_lot_Admiral"], [mt5.TIMEFRAME_M1], True
        )
        DATA_TF_1 = DATA[TF_list[0]][symbol]
    else:
        DATA_TF_1 = DATA[TF_list[0]]

    PIPS = 0.0001
    LAST_CANDLE_FIRST_TF = Candle(DATA_TF_1.iloc[-1], bollinger_band=True, RSI=True)

    #######################
    ###### Bot strat ######
    #######################
    comment = "RSI_bot"
    size = 0.29
    be = None
    tp = None
    sl = None
    SL_PIPS = 2 * PIPS
    if backtest_data is None:
        manage_personnal_bot(last_candle=LAST_CANDLE_FIRST_TF, sl_pips=SL_PIPS)
    ###########if you want your bot to trade only between specified hours##########
    LAST_CANDLE_HOUR = LAST_CANDLE_FIRST_TF.date.hour
    if LAST_CANDLE_HOUR < interval_hour[0] or LAST_CANDLE_HOUR >= interval_hour[1]:
        return None
    ###############################################################################
    RSI_OVERLOAD = 70
    RSI_UNDERLOAD = 30

    if (
        LAST_CANDLE_FIRST_TF.RSI > RSI_OVERLOAD
        and LAST_CANDLE_FIRST_TF.close > LAST_CANDLE_FIRST_TF.uper_bollinger
        and LAST_CANDLE_FIRST_TF.open > LAST_CANDLE_FIRST_TF.uper_bollinger
    ):
        order_type = mt5.ORDER_TYPE_SELL
        price = LAST_CANDLE_FIRST_TF.close
        sl = price + SL_PIPS
        tp = price - SL_PIPS*2

    elif (
        LAST_CANDLE_FIRST_TF.RSI < RSI_UNDERLOAD
        and LAST_CANDLE_FIRST_TF.close < LAST_CANDLE_FIRST_TF.lower_bollinger
        and LAST_CANDLE_FIRST_TF.open < LAST_CANDLE_FIRST_TF.lower_bollinger
    ):
        order_type = mt5.ORDER_TYPE_BUY
        price = LAST_CANDLE_FIRST_TF.close
        sl = price - SL_PIPS
        tp = price + SL_PIPS*2
    else:
        return None

    ####################
    ### Taking trade ###
    ####################

    if backtest_data is None:
        sl = None
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

        info_trade = {
            "order_type": order_type,
            "date_entry": str(LAST_CANDLE_FIRST_TF.date),
            "price": float(price),
            "RR": None,
            "be": be,
            "tp": float(tp),
            "original_sl": float(SL_PIPS),
            "sl": float(sl),
            "pending": False,
            "on_going": True,
            "sl_to_be": False,
            "sl_ratio_modified": 1,  # if your sl is not modified in your managment, let 1 by default
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


def check_sl_be_tp_backtest(trade_info: Dict, last_candle: Candle):
    trade_closing = False
    result_trade = None
    PIPS = 0.0001
    if trade_info["order_type"] == mt5.ORDER_TYPE_SELL:

        if last_candle.high >= trade_info["sl"]:
            trade_closing = True
            '''
            trade_info["sl_ratio_modified"] = float(
                (last_candle.close - trade_info["price"]) / trade_info["original_sl"]
            )
            '''
            result_trade = "sl"
            return trade_info, trade_closing, result_trade
        
        if last_candle.low < trade_info["tp"]:
            trade_closing = True
            result_trade = "tp"
            trade_info["RR"] = float(
                abs((trade_info["tp"] - trade_info["price"]))
                / trade_info["original_sl"]
            )
        
    elif trade_info["order_type"] == mt5.ORDER_TYPE_BUY:

        if last_candle.low <= trade_info["sl"]:
            trade_closing = True
            '''
            trade_info["sl_ratio_modified"] = float(
                (trade_info["price"] - last_candle.close) / trade_info["original_sl"]
            )
            '''
            result_trade = "sl"
            return trade_info, trade_closing, result_trade
        
        if last_candle.high > trade_info["tp"]:
            trade_closing = True
            result_trade = "tp"
            trade_info["RR"] = float(
                abs((trade_info["tp"] - trade_info["price"]))
                / trade_info["original_sl"]
            )
        

    return trade_info, trade_closing, result_trade


def check_sl_be_live(trade, sl_pips, last_candle):
    order_type = trade.type
    entering_price = trade.price_open
    sl_to_be = False
    trade_closing = False
    PIPS = 0.0001
    if order_type == mt5.ORDER_TYPE_SELL:
        if entering_price < last_candle.close - sl_pips:
            trade_closing = True
        elif (
            last_candle.close < last_candle.middle_bollinger
            and entering_price > last_candle.close + 1 * PIPS
        ):
            sl_to_be = True
    elif order_type == mt5.ORDER_TYPE_BUY:
        if entering_price > last_candle.close + sl_pips:
            trade_closing = True
        elif (
            last_candle.close > last_candle.middle_bollinger
            and entering_price < last_candle.close - 1 * PIPS
        ):
            sl_to_be = True

    return trade_closing, sl_to_be


def manage_personal_bot(trade_info: Optional[Dict] = None, **kwargs):
    """
    manage on going trade and return True if a trade is on going
    """
    PIPS = 0.0001
    if trade_info is not None:
        DATA = return_datas(
            [kwargs["symbol"]],
            [mt5.TIMEFRAME_M1],
            False,
            None,
            kwargs["backtest_data"],
            kwargs["bollinger_band"],
            kwargs["RSI"],
        )
        DATA_TF_1 = DATA[mt5.TIMEFRAME_M1]
        trade_closing = False
        result_trade = None
        LAST_CANDLE = Candle(DATA_TF_1.iloc[-1], bollinger_band=True, RSI=True)
        trade_info, trade_closing, result_trade = check_sl_be_tp_backtest(
            trade_info, LAST_CANDLE
        )
        return trade_info, trade_closing, result_trade

    else:
        all_trade_on_going = positions_get()
        for trade in all_trade_on_going.iloc():
            comment_trade = trade["comment"]
            if comment_trade != "Bollinger_bot":
                continue
            sl = kwargs["sl_pips"]
            trade_closing, sl_to_be = check_sl_be_live(trade, sl, kwargs["last_candle"])
            if trade_closing:
                trade_is_closed = close_one_trade_on_going(trade)
                if trade_is_closed:
                    print(colored(f"succesfully closed trade : \n{trade}", "green"))
            if sl_to_be:
                move_sl_to_be(trade, 0.3 * PIPS)


def live_trading_personnal_strat(
    account_currency: str, risk: float, symbols: List[str]
):
    """
    launch the bot every minute
    """
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
                my_personnal_bot_strategy,
                my_account,
                symbol,
                account_currency,
                risk,
            )
        )
    while True:
        schedule.run_pending()
        time.sleep(1)
