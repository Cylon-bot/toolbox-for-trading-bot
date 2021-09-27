from datetime import datetime, timedelta
import pytz
import MetaTrader5 as mt5
from typing import List, Optional, Union, Tuple, Dict
from progress.bar import FillingCirclesBar
import yaml
import os
import sys
import inspect
import pandas as pd
from copy import deepcopy
from tools.market_data import load_data, get_data
from tools.candle import Candle
from termcolor import colored
from bot_strat import bot_strategy
from pathlib import Path


def create_backtest():
    """
    create your backtest here, you have an example with the bot_strat already implemented
    """
    symbol_backtest = "EURUSD"
    period_backtest = "january_2021"
    name_strat = "bot_strat_example"
    risk = 0.5
    path_data = "january_2021.txt"
    initial_account_balance = 100_000
    time_frame = mt5.TIMEFRAME_M1
    more_than_on_trade_on_going = True
    delete_previous_pending_trade = False
    # here you need to create a dictionary with the name of the parameter in your strat function as key and input as value
    # you don't have to put the parameters inside kwargs if they are already initialized and you don't want to change them
    # exemple : I don't put the parameter my_account because I want the initalized value None
    # don't put backtest_data parameter, it will be automatically fill by the backest class (PS : don't rename this parameter)
    kwargs = {
        "symbol": ["EURUSD"],
        "risk": risk,
        "TF_list": [time_frame],
        "EMA_list": [50],
    }
    Backtest(
        symbol_backtest,
        period_backtest,
        name_strat,
        risk,
        initial_account_balance,
        time_frame,
        more_than_on_trade_on_going,
        delete_previous_pending_trade,
        **kwargs,
    )
    name_file_data = "January_2021.txt"
    ABSOLUTE_PATH_LAUNCH = Path.cwd()
    path_data = (
        ABSOLUTE_PATH_LAUNCH
        / "backtest"
        / "data_candles"
        / symbol_backtest
        / name_file_data
    )
    Backtest.launch_backtest(path_data)


class AccountBacktest:
    """
    regroup info of the backtest account
    """

    def __init__(self, initial_balance: float):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.max_balance_until_now = initial_balance


class Backtest:
    """
    class which create a backtest of a given symbol, strategy, and diverse parameters
    """

    def __init__(
        self,
        symbol_backtest: str,
        period_backtest: str,
        backtest_name: str,
        risk_backtest: float,
        initial_account_balance: float,
        time_frame: int,
        more_than_on_trade_on_going: bool,
        delete_previous_pending_trade: bool,
        **kwargs,
    ):
        self.symbol = symbol_backtest
        self.backtest_name = backtest_name
        self.account = AccountBacktest(initial_account_balance)
        self.period_backtest = period_backtest
        PERCENTAGE_CONVERSION = 0.01
        self.risk_percentage = risk_backtest * PERCENTAGE_CONVERSION
        self.max_drawdown = 0
        self.max_drawdown_percentage = 0
        self.time_frame = time_frame
        self.info_trade = None
        self.info_all_trade = {}
        self.delete_previous_pending_trade = delete_previous_pending_trade
        self.more_than_on_trade_on_going = more_than_on_trade_on_going
        self.trade_on_going = False
        self.kwargs = kwargs

    def launch_backtest(self, path_data: str) -> (float, float):
        """
        launch backtest on the period of time and symbol specified
        Only work for a unique timeframe for now. Work in progress...
        """
        data_candles_all_tf = load_data(path_data)
        data_candles = dict()
        for tf, data_candles_pairs in data_candles_all_tf.items():
            data_candles[tf] = data_candles_pairs[self.symbol]
        PREVIOUS_BACKTEST_CANDLE_EXISTING = 100
        DATA = data_candles[self.time_frame]
        MAX_ITERATOR_BACKTEST = len(DATA.index) - PREVIOUS_BACKTEST_CANDLE_EXISTING
        progress_bar = FillingCirclesBar("Processing", max=MAX_ITERATOR_BACKTEST + 1)
        data_step_to_process = {}
        for step_backtest in range(MAX_ITERATOR_BACKTEST + 1):
            data_step_to_process[f"TF {self.time_frame}"] = DATA.iloc[
                step_backtest : PREVIOUS_BACKTEST_CANDLE_EXISTING + step_backtest
            ]
            self.launch_strategy(data_step_to_process)
            progress_bar.next()

        progress_bar.finish()
        message = self.create_message()
        print(message)
        self.write_txt(message, self.info_all_trade)
        return (self.account.balance, self.max_drawdown_percentage)

    def create_message(self) -> str:
        """
        create a string message with all the info of the backtest
        """
        ONE_HUNDRED = 100
        number_trades = len(self.info_all_trade)
        win_number = 0
        loose_number = 0
        for id_trade, trade in self.info_all_trade.items():
            if trade["win"]:
                win_number += 1
            elif not trade["win"]:
                loose_number += 1
        if number_trades == 0:
            win_ratio = "Nan"
        else:
            win_ratio = (round(win_number / (number_trades), 2)) * ONE_HUNDRED
        message = (
            f"Strategy used: {self.backtest_name}\n"
            f"Symbol Backtested: {self.symbol}\n"
            f"Period Backtested: {self.period_backtest}\n"
            f"Times frame used: {self.time_frame}\n"
            f"Initial balance: {self.account.initial_balance}\n"
            f"Balance after backtest: {self.account.balance:.2f}\n"
            f"Risk taken for each trade: {self.risk_percentage*ONE_HUNDRED}\n"
            f"Number of trade taken: {number_trades}\n"
            f"Number of wins: {win_number}\n"
            f"Number of looses: {loose_number}\n"
            f"win/loose ratio: {win_ratio} %\n"
            f"Max drawdown: {self.max_drawdown:.2f}\n"
            f"Max drawdown percentage: {self.max_drawdown_percentage:.2f} %\n"
            f"\n{'-'*ONE_HUNDRED}\n\n"
        )
        return message

    def write_txt(self, message: str, all_trade_info: Dict):
        """
        save a txt file with all the info of the backtest
        save a yaml with all trade infos taken on the period of time of the backtest
        """
        if not os.path.exists(f"backtest/backtest_by_symbol/{self.symbol}"):
            os.makedirs(f"backtest/backtest_by_symbol/{self.symbol}")

        if not os.path.exists(
            f"backtest/backtest_by_symbol/{self.symbol}/{self.backtest_name}"
        ):
            os.makedirs(
                f"backtest/backtest_by_symbol/{self.symbol}/{self.backtest_name}"
            )

        if not os.path.exists(f"backtest/all_trade_backtest/{self.symbol}"):
            os.makedirs(f"backtest/all_trade_backtest/{self.symbol}")

        if not os.path.exists(
            f"backtest/all_trade_backtest/{self.symbol}/{self.backtest_name}"
        ):
            os.makedirs(
                f"backtest/all_trade_backtest/{self.symbol}/{self.backtest_name}"
            )

        with open(
            f"backtest/backtest_by_symbol/{self.symbol}/{self.backtest_name}.txt", "a"
        ) as text_file:
            text_file.write(message)

        with open(
            f"backtest/all_trade_backtest/{self.symbol}/{self.backtest_name}.yaml",
            "w",
        ) as yaml_file:
            yaml_save = yaml.dump(message_all_trade, yaml_file)

    def check_if_trade_is_on_going(self, trade, last_candle: Candle) -> Dict:
        """
        check if a trade pending is now on going
        """
        order_type = trade["order_type"]
        if (
            (
                order_type == mt5.ORDER_TYPE_BUY_LIMIT
                or order_type == mt5.ORDER_TYPE_SELL_STOP
            )
            and trade["pending"]
            and not trade["on_going"]
        ):
            if last_candle.low <= trade["price"]:
                trade["on_going"] = True
                trade["pending"] = False
                self.trade_on_going = True
        elif (
            (
                order_type == mt5.ORDER_TYPE_SELL_LIMIT
                or order_type == mt5.ORDER_TYPE_BUY_STOP
            )
            and trade["pending"]
            and not trade["on_going"]
        ):
            if last_candle.high >= trade["price"]:
                trade["on_going"] = True
                trade["pending"] = False
                self.trade_on_going = True
        return trade

    def check_if_trade_need_closing(
        self, trade: Dict, last_candle: Candle
    ) -> (bool, str):
        """
        check if a trade on going is now closed by SL, TP or BE
        """
        trade_closing = False
        result_trade = None
        order_type = trade["order_type"]
        if (
            order_type == mt5.ORDER_TYPE_BUY
            or order_type == mt5.ORDER_TYPE_BUY_LIMIT
            or order_type == mt5.ORDER_TYPE_BUY_STOP
        ):
            if last_candle.low < trade["sl"]:
                trade_closing = True
                result_trade = "sl"
            elif last_candle.high > trade["tp"]:
                trade_closing = True
                result_trade = "tp"
        elif (
            order_type == mt5.ORDER_TYPE_SELL
            or order_type == mt5.ORDER_TYPE_SELL_LIMIT
            or order_type == mt5.ORDER_TYPE_SELL_STOP
        ):
            if last_candle.high > trade["sl"]:
                trade_closing = True
                result_trade = "sl"
            elif last_candle.low < trade["tp"]:
                trade_closing = True
                result_trade = "tp"
        return trade_closing, result_trade

    def manage_balance_after_trade_closing(
        self, trade: Dict, result_trade: str, RR: float
    ):
        """
        change the balance depending if the trade is SL, TP or BE
        """
        if result_trade == "tp":
            new_balance = (
                self.account.balance + self.account.balance * self.risk_percentage * RR
            )
        elif result_trade == "sl":
            if trade["sl_to_be"]:
                new_balance = self.account.balance - (
                    self.account.balance
                    * self.risk_percentage
                    * 0.05  # 0.05 simulate the fee of the broker even if you are at BE
                )
            else:
                new_balance = (
                    self.account.balance - self.account.balance * self.risk_percentage
                )
        return new_balance

    def check_if_trade_is_win(self, trade: Dict, new_balance: float) -> Dict:
        """
        check if the trade is win or loose
        """
        if new_balance > self.account.balance:
            trade["win"] = True
        else:
            trade["win"] = False
        return trade

    def check_if_trade_sl_to_be(self, trade: Dict, last_candle: Candle) -> Dict:
        """
        check if the trade SL need to be put at BE
        """
        order_type = trade["order_type"]
        if (
            order_type == mt5.ORDER_TYPE_BUY
            or order_type == mt5.ORDER_TYPE_BUY_LIMIT
            or order_type == mt5.ORDER_TYPE_BUY_STOP
        ):
            if last_candle.close >= trade["be"]:
                trade["sl_to_be"] = True
                trade["sl"] = trade["price"]
        elif (
            order_type == mt5.ORDER_TYPE_SELL
            or order_type == mt5.ORDER_TYPE_SELL_LIMIT
            or order_type == mt5.ORDER_TYPE_SELL_STOP
        ):
            if last_candle.close <= trade["be"]:
                trade["sl_to_be"] = True
                trade["sl"] = trade["price"]
        return trade

    def manage_drawdown(self):
        """
        manage max drawdown of the backtest
        """
        if self.account.max_balance_until_now < self.account.balance:
            self.account.max_balance_until_now = self.account.balance

        if (
            (self.account.max_balance_until_now - self.account.balance)
            / self.account.max_balance_until_now
        ) * 100 > self.max_drawdown_percentage:
            self.max_drawdown = (
                self.account.max_balance_until_now - self.account.balance
            )
            self.max_drawdown_percentage = (
                self.max_drawdown / self.account.max_balance_until_now
            ) * 100

    def manage_on_going_trades(self, last_candle: Candle):
        """
        manage on going trade --> SL, TP or BE
        """
        for trade_id, trade in self.info_all_trade.items():
            if not trade["on_going"] and not trade["pending"]:
                continue
            if trade["pending"]:
                trade = self.check_if_trade_is_on_going(trade, last_candle)
            if not trade["on_going"]:
                continue
            trade_closing, result_trade = self.check_if_trade_need_closing(
                trade, last_candle
            )
            RR = trade["RR"]
            if trade_closing:
                new_balance = self.manage_balance_after_trade_closing(
                    trade, result_trade, RR
                )
                trade = self.check_if_trade_is_win(trade, new_balance)
                self.account.balance = new_balance
                trade["on_going"] = False
                self.trade_on_going = False
            else:
                trade = self.check_if_trade_sl_to_be(trade, last_candle)
            self.manage_drawdown()

    def launch_strategy(self, data_step_to_process: dict[str, pd.DataFrame]):
        """
        launch the strategy and manage result of trades
        """
        DATA_TF = data_step_to_process[f"TF {self.time_frame}"]
        LAST_CANDLE = Candle(DATA_TF.iloc[-1])
        self.kwargs["backtest_data"] = DATA_TF
        self.manage_on_going_trades(LAST_CANDLE)
        if not self.trade_on_going or self.more_than_on_trade_on_going:
            trade = bot_strategy(**self.kwargs)
        else:
            trade = None
        if trade is not None:
            if self.delete_previous_pending_trade:
                self.info_all_trade = dict(
                    (key, value)
                    for (key, value) in self.info_all_trade.items()
                    if not value["pending"]
                )
            info_trade_deep_copy = deepcopy(trade)
            self.info_all_trade[
                str(LAST_CANDLE.date) + str(trade["order_type"])
            ] = info_trade_deep_copy
