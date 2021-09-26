import MetaTrader5 as mt5
from termcolor import colored
from typing import List, Optional
import pandas as pd
from tools.market_data import return_datas
from tools.tools_trade import positions_get
from account import Account
from tools.candle import Candle
from random import choice
import schedule
from trade import Trade
import time



def bot_strategy(
    my_account: Optional[Account],
    pair: str = "EURUSD-Z",
    account_currency: str = "USD",
    risk: float = 0.5,
    TF_list: list[int] = [mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M15],
    backtest_data: Optional[dict[str, pd.DataFrame]] = None,
    EMA_list: Optional[List[int]] = None,
    bollinger_band: bool = False,
) -> Optional[dict[str,Union[bool, str, floatn int]]]:
    '''
        put your strat here 
    '''
    DATA = return_datas([pair], TF_list, False, EMA_list, backtest_data, bollinger_band)
    if backtest_data is None:
        LOT_ALL_PAIR = return_datas([pair], [mt5.TIMEFRAME_M1], True)
    else:
        DATA_TF_1 = DATA[TF_list[0]]
        DATA_TF_5 = DATA[TF_list[1]]
        DATA_TF_15 = DATA[TF_list[2]]

    PIPS = 0.0001
    MICRO_PIPS = 0.00001


    LAST_CANDLE_FIRST_TF = Candle(DATA[TF_list[0]].iloc[-1])
    

    #if you want your bot to trade only between 9H and 17H (8 and 16 on mt5)
    last_candle_hour = LAST_CANDLE_FIRST_TF.date.hour
    if (last_candle_hour < 9 or last_candle_hour > 17) :
        return None

    #####################
    ### Bot strat #######
    #####################
    order_type = mt5.ORDER_TYPE_SELL_LIMIT
    price = None
    tp = None
    sl = None
    size = None
    comment = 'my bot trade'
    ####################
    ### Taking trade ###
    ####################

    if backtest_data is None :
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
            LOT_ALL_PAIR,
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
) -> [bool, "MqlTradeRequest"]:
   '''
        create a new trade and open it
   '''
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
        my_account, account_currency, risk, lot_all_pair, size = size
    )
    return new_trade_is_open, result


def live_trading(account_currency: str, risk: float, pair_list: List[str], normal_account):
    '''
        launch the bot every minute  
    '''
    my_account = Account(account_currency=account_currency, original_risk=risk, normal_account = normal_account)
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