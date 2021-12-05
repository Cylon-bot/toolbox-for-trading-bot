from datetime import datetime, timedelta
import MetaTrader5 as Mt5
import pandas as pd
from typing import List, Dict, Optional, Union
from pathlib import Path
import pickle as pck
import pytz
import talib as ta

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


def get_data(
    symbols: List[str],
    time_frame: int,
    utc_from: datetime,
    date_to: datetime,
    ema_list: Optional[List[int]] = None,
    backtest: bool = False,
    backtest_data: Optional[pd.DataFrame] = None,
    bollinger_band: bool = False,
    rsi: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    ask to the mt5 server for the data and add any specified indicator from ta-lib libraries
    indicator implemented at the moment :

        - EMA
        - bollinger band
    """
    pair_data = dict()
    if not backtest:
        for pair in symbols:
            date_to = datetime(
                date_to.year,
                date_to.month,
                date_to.day,
                hour=date_to.hour,
                minute=date_to.minute,
            )
            rates = Mt5.copy_rates_range(pair, time_frame, utc_from, date_to)
            rates_frame = pd.DataFrame(rates)
            rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")
            rates_frame.drop(rates_frame.tail(1).index, inplace=True)
            pair_data[pair] = rates_frame
    else:
        pair_data = backtest_data[f"TF {time_frame}"]

    if ema_list is not None:
        for ema in ema_list:
            pair_data = add_ema_to_data(pair_data, backtest=backtest, ema=ema)
    if bollinger_band:
        pair_data = add_bollinger_to_data(pair_data, backtest=backtest)

    if rsi:
        pair_data = add_rsi_to_data(pair_data, backtest=backtest)
    return pair_data


def get_time_frame_needed(tf: int = Mt5.TIMEFRAME_M1) -> Dict[int, datetime]:
    """
    return three day of candles in a specified TF
    """
    now = datetime.now().astimezone(pytz.timezone("Etc/GMT-5"))
    now = datetime(now.year, now.month, now.day, hour=now.hour, minute=now.minute)
    three_day = now - timedelta(hours=72)
    tf_from_date = {tf: three_day}
    return tf_from_date


def return_datas(
    symbols: List[str],
    tf_list: list[int],
    datas_for_lot: bool,
    ema_list: Optional[List[int]] = None,
    backtest_data: Optional[pd.DataFrame] = None,
    bollinger_band: bool = False,
    rsi: bool = False,
) -> Union[Dict[int, Dict[str, pd.DataFrame]], Dict[str, pd.DataFrame]]:
    """
    return datas candles with specified information. If we need to return
    information for size lot it will only be the last candle.
    """
    if backtest_data is not None:
        backtest = True
    else:
        backtest = False
    data_candles_all_tf = dict()
    date_to = datetime.now().astimezone(pytz.timezone("Etc/GMT-5"))
    for TF in tf_list:
        tf_from_date = get_time_frame_needed(TF)
        for time_frame, from_date in tf_from_date.items():
            data_candles_all_tf[time_frame] = get_data(
                symbols,
                time_frame,
                from_date,
                date_to,
                ema_list,
                backtest,
                backtest_data,
                bollinger_band,
                rsi,
            )
    if datas_for_lot:
        last_row_lot_all_pair = dict()
        for tf, data_candles in data_candles_all_tf.items():
            for pair, pair_data in data_candles.items():
                last_row_lot = pair_data.tail(1)
                last_row_lot_all_pair[pair] = last_row_lot
        return last_row_lot_all_pair
    else:
        return data_candles_all_tf


def add_ema_to_data(
    data_candles_all_tf: dict, backtest: bool = False, ema: int = 50
) -> Dict[str, pd.DataFrame]:
    """
    add specified EMA to data candles
    """
    string_ema = str(ema)
    if backtest:
        data_candles_all_tf["EMA" + string_ema] = ta.EMA(
            data_candles_all_tf["close"], ema
        )

    else:
        for pair, pair_data in data_candles_all_tf.items():
            pair_data["EMA" + string_ema] = ta.EMA(pair_data["close"], ema)
    return data_candles_all_tf


def add_bollinger_to_data(data_candles_all_tf: dict, backtest: bool = False):
    """
    add specified bollinger band to data candles
    """
    if backtest:
        (
            data_candles_all_tf["upper_bollinger"],
            data_candles_all_tf["middle_bollinger"],
            data_candles_all_tf["lower_bollinger"],
        ) = ta.BBANDS(
            data_candles_all_tf["close"],
            timeperiod=20,
            matype=0,
            nbdevup=2,
            nbdevdn=2,
        )

    else:
        for pair, pair_data in data_candles_all_tf.items():
            (
                pair_data["upper_bollinger"],
                pair_data["middle_bollinger"],
                pair_data["lower_bollinger"],
            ) = ta.BBANDS(
                pair_data["close"],
                timeperiod=20,
                matype=0,
                nbdevup=2,
                nbdevdn=2,
            )
    return data_candles_all_tf


def add_rsi_to_data(
    data_candles_all_tf: dict, backtest: bool = False, time_period: int = 14
):
    """
    add specified rsi band to data candles
    """
    if backtest:
        data_candles_all_tf["RSI"] = ta.RSI(
            data_candles_all_tf["close"],
            timeperiod=time_period,
        )
    else:
        for pair, pair_data in data_candles_all_tf.items():
            pair_data["RSI"] = ta.RSI(
                pair_data["close"],
                timeperiod=time_period,
            )
    return data_candles_all_tf


def save_data(data: Dict[str, pd.DataFrame], path_output: Path):
    """
    Export pandas data to a file with pickle.
    """
    with open(path_output, "wb") as file:
        pck.dump(data, file)


def load_data(path_output: Path):
    """
    Read input data from a text file with pickle and export them as pandas data.
    """
    with open(path_output, "rb") as FILE:
        return pck.load(FILE)
