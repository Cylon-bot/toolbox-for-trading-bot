from datetime import datetime, timedelta
import MetaTrader5 as mt5
import pandas as pd
from typing import List, Dict, Optional, Union
import os
from pathlib import Path
import pickle as pck
import pytz
import talib as ta


def get_data(
    pairs: List[str],
    time_frame: int,
    utc_from: datetime,
    date_to: datetime,
    EMA_list: Optional[List[int]] = None,
    backtest: bool = False,
    backtest_data: Optional[pd.DataFrame] = None,
    bollinger_band: bool = False,
) -> Dict[str, pd.DataFrame]:
    """
    ask to the mt5 server for the data and add any specified indicator from talib librarie
    indicator implemented at the moment :

        - EMA
        - bollinger band
    """
    pair_data = dict()
    if not backtest:
        for pair in pairs:
            date_to = datetime(
                date_to.year,
                date_to.month,
                date_to.day,
                hour=date_to.hour,
                minute=date_to.minute,
            )

            rates = mt5.copy_rates_range(pair, time_frame, utc_from, date_to)
            rates_frame = pd.DataFrame(rates)
            rates_frame["time"] = pd.to_datetime(rates_frame["time"], unit="s")
            rates_frame.drop(rates_frame.tail(1).index, inplace=True)
            pair_data[pair] = rates_frame
    else:
        pair_data = backtest_data[f"TF {time_frame}"]
    if EMA_list is not None:
        for EMA in EMA_list:
            if backtest:
                pair_data = add_EMA_to_data(pair_data, backtest=backtest, EMA=EMA)
            else:
                pair_data = add_EMA_to_data(pair_data, backtest=backtest, EMA=EMA)
    if bollinger_band:
        if backtest:
            pair_data = add_bollinger_to_data(pair_data, backtest=backtest)
        else:
            pair_data = add_bollinger_to_data(pair_data, backtest=backtest)
    return pair_data


def get_time_frame_needed(TF: int = mt5.TIMEFRAME_M1) -> Dict[int, datetime]:
    """
    return three day of candles in a specifie TF
    """
    now = datetime.now().astimezone(pytz.timezone("Etc/GMT-5"))
    now = datetime(now.year, now.month, now.day, hour=now.hour, minute=now.minute)
    three_day = now - timedelta(hours=72)
    TF_FROM_DATE = {TF: three_day}
    return TF_FROM_DATE


def return_datas(
    pairs: List[str],
    TF_list: list[int],
    datas_for_lot: bool,
    EMA_list: Optional[List[int]] = None,
    backtest_data: Optional[pd.DataFrame] = None,
    bollinger_band: bool = False,
) -> Union[Dict[int, Dict[str, pd.DataFrame]], Dict[str, pd.DataFrame]]:
    """
    return datas candles with specifie information. If we need to return
    information for size lot it will only be the last candle.
    """
    if backtest_data is not None:
        backtest = True
    else:
        backtest = False
    data_candles_all_tf = dict()
    date_to = datetime.now().astimezone(pytz.timezone("Etc/GMT-5"))
    for TF in TF_list:
        TF_FROM_DATE = get_time_frame_needed(TF)
        for time_frame, from_date in TF_FROM_DATE.items():
            data_candles_all_tf[time_frame] = get_data(
                pairs,
                time_frame,
                from_date,
                date_to,
                add_EMA,
                EMA_list,
                backtest,
                backtest_data,
                bollinger_band,
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


def add_EMA_to_data(
    data_candles_all_tf: dict, backtest: bool = False, EMA: int = 50
) -> Dict[str, pd.DataFrame]:
    """
    add specified EMA to data candles
    """
    STRING_EMA = str(EMA)
    if backtest:
        data_candles_all_tf["EMA" + STRING_EMA] = ta.EMA(
            data_candles_all_tf["close"], EMA
        )

    else:
        for pair, pair_data in data_candles_all_tf.items():
            pair_data["EMA" + STRING_EMA] = ta.EMA(pair_data["close"], EMA)
    return data_candles_all_tf


def add_bollinger_to_data(data_candles_all_tf: dict, backtest: bool = False):
    """
    add specified bollinger band to data candles
    """
    if backtest:
        (
            data_candles_all_tf["uper_bollinger"],
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
                pair_data["uper_bollinger"],
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


def save_data(DATA: Dict[str, pd.DataFrame], PATH_OUTPUT: Path):
    """
    Export pandas data to a file with pickle.
    """
    with open(PATH_OUTPUT, "wb") as file:
        pck.dump(DATA, file)


def load_data(path_output: Path):
    """
    Read input data from a text file with pickle and export them as pandas data.
    """
    with open(path_output, "rb") as FILE:
        return pck.load(FILE)
