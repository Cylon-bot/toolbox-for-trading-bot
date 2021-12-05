import MetaTrader5 as Mt5
from typing import Dict, Optional, Union
from progress.bar import FillingCirclesBar
import yaml
import os
import pandas as pd
from copy import deepcopy
from tools.market_data import load_data
from tools.candle import Candle

from pathlib import Path

try:
    from personal_bot import my_personal_bot_strategy as bot_strategy, manage_personal_bot as manage_bot
except ImportError:
    from bot_strat import bot_strategy, manage_bot

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


def create_backtest():
    """
    create your backtest here, you have an example
    with the bot_strat already implemented
    """

    # Modify this part
    ##############################################################
    symbol_backtest = "EURUSD"
    period_backtest = "January_2021"
    name_strat = "bot_strat_example"
    risk = 0.5
    name_file_data = "January_2021.txt"
    initial_account_balance = 100_000
    time_frame = Mt5.TIMEFRAME_M1
    more_than_on_trade_on_going = False
    unique_id_backtest = "January_2021"
    delete_previous_pending_trade = False
    strat_auto_manage_trade = False
    # here you need to create a dictionary with the name of the
    # parameters in your strat function as key and input as value
    # you don't have to put the parameters inside kwargs if they
    # are already initialized and you don't want to change them
    # example : I don't put the parameter my_account because I
    # want the initialized value None
    # don't put backtest_data parameter, it will be automatically
    # fill by the backest class (PS : don't rename this parameter)
    kwargs = {
        "symbol": "EURUSD",
        "risk": risk,
        "TF_list": [time_frame],
        "EMA_list": [25, 50],
    }

    # Normally you don't have to modify this part
    ##############################################################
    my_backtest = Backtest(
        symbol_backtest,
        period_backtest,
        name_strat,
        unique_id_backtest,
        risk,
        initial_account_balance,
        time_frame,
        more_than_on_trade_on_going,
        delete_previous_pending_trade,
        strat_auto_manage_trade,
        **kwargs,
    )

    absolute_path_launch = Path.cwd()
    path_data = (
        absolute_path_launch
        / "backtest"
        / "data_candles"
        / symbol_backtest
        / name_file_data
    )
    my_backtest.launch_backtest(path_data)


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
    class which create a backtest of a given symbol,
    strategy, and diverse parameters
    """

    def __init__(
        self,
        symbol_backtest: str,
        period_backtest: str,
        backtest_name: str,
        unique_id_backtest: str,
        risk_backtest: float,
        initial_account_balance: float,
        time_frame: int,
        more_than_on_trade_on_going: bool,
        delete_previous_pending_trade: bool,
        strat_auto_manage_trade: bool,
        **kwargs,
    ):
        self.symbol = symbol_backtest
        self.backtest_name = backtest_name
        self.unique_id_backtest = unique_id_backtest
        self.account = AccountBacktest(initial_account_balance)
        self.period_backtest = period_backtest
        percentage_conversion = 0.01
        self.risk_percentage = risk_backtest * percentage_conversion
        self.max_drawdown = 0
        self.max_drawdown_percentage = 0
        self.time_frame = time_frame
        self.info_trade = None
        self.info_all_trade = {}
        self.delete_previous_pending_trade = delete_previous_pending_trade
        self.more_than_on_trade_on_going = more_than_on_trade_on_going
        self.trade_on_going = False
        self.kwargs = kwargs
        self.strat_auto_manage_trade = strat_auto_manage_trade

    def launch_backtest(self, path_data: Union[Path, str]) -> (float, float):
        """
        launch backtest on the period of time and symbol specified
        Only work for a unique timeframe for now. Work in progress...
        """
        data_candles_all_tf = load_data(path_data)
        data_candles = dict()
        for tf, data_candles_pairs in data_candles_all_tf.items():
            data_candles[tf] = data_candles_pairs[self.symbol]
        previous_backtest_candle_existing = 100
        data = data_candles[self.time_frame]
        max_iterator_backtest = len(data.index) - previous_backtest_candle_existing
        progress_bar = FillingCirclesBar("Processing", max=max_iterator_backtest + 1)
        data_step_to_process = {}
        for step_backtest in range(max_iterator_backtest + 1):
            data_step_to_process[f"TF {self.time_frame}"] = data.iloc[
                step_backtest: previous_backtest_candle_existing + step_backtest
            ]
            self.launch_strategy(data_step_to_process)
            progress_bar.next()

        progress_bar.finish()
        message = self.create_message()
        print(message)
        self.write_txt(message, self.info_all_trade)
        return self.account.balance, self.max_drawdown_percentage

    def create_message(self) -> str:
        """
        create a string message with all the info of the backtest
        """
        one_hundred = 100
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
            win_ratio = (round(win_number / number_trades, 2)) * one_hundred
        message = (
            f"Strategy used: {self.backtest_name}\n"
            f"id backtest used: {self.unique_id_backtest}\n"
            f"Symbol Backtested: {self.symbol}\n"
            f"Period Backtested: {self.period_backtest}\n"
            f"Times frame used: {self.time_frame}\n"
            f"Initial balance: {self.account.initial_balance}\n"
            f"Balance after backtest: {self.account.balance:.2f}\n"
            f"Risk taken for each trade: {self.risk_percentage*one_hundred}\n"
            f"Number of trade taken: {number_trades}\n"
            f"Number of wins: {win_number}\n"
            f"Number of looses: {loose_number}\n"
            f"win/loose ratio: {win_ratio} %\n"
            f"Max drawdown: {self.max_drawdown:.2f}\n"
            f"Max drawdown percentage: {self.max_drawdown_percentage:.2f} %\n"
            f"\n{'-'*one_hundred}\n\n"
        )
        return message

    def write_txt(self, message: str, all_trade_info: Dict):
        """
        save a txt file with all the info of the backtest
        save a yaml with all trades infos taken on the period of time of the backtest
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

        with open(
            f"backtest/backtest_by_symbol/{self.symbol}/{self.backtest_name}/{self.unique_id_backtest}.txt",
            "a",
        ) as text_file:
            text_file.write(message)

        with open(
            f"backtest/all_trade_backtest/{self.symbol}/{self.backtest_name}.yaml",
            "w",
        ) as yaml_file:
            yaml.dump(all_trade_info, yaml_file)

    def check_if_trade_is_on_going(self, trade, last_candle: Candle) -> Dict:
        """
        check if a trade pending is now on going
        """
        order_type = trade["order_type"]
        if (
            (
                order_type == Mt5.ORDER_TYPE_BUY_LIMIT
                or order_type == Mt5.ORDER_TYPE_SELL_STOP
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
                order_type == Mt5.ORDER_TYPE_SELL_LIMIT
                or order_type == Mt5.ORDER_TYPE_BUY_STOP
            )
            and trade["pending"]
            and not trade["on_going"]
        ):
            if last_candle.high >= trade["price"]:
                trade["on_going"] = True
                trade["pending"] = False
                self.trade_on_going = True
        return trade

    @staticmethod
    def check_if_trade_need_closing(
            trade: Dict, last_candle: Candle
    ) -> (bool, str):
        """
        check if a trade on going is now closed by SL, TP or BE
        """
        trade_closing = False
        result_trade = None
        order_type = trade["order_type"]
        if (
            order_type == Mt5.ORDER_TYPE_BUY
            or order_type == Mt5.ORDER_TYPE_BUY_LIMIT
            or order_type == Mt5.ORDER_TYPE_BUY_STOP
        ):
            if last_candle.low < trade["sl"]:
                trade_closing = True
                result_trade = "sl"
            elif last_candle.high > trade["tp"]:
                trade_closing = True
                result_trade = "tp"
        elif (
            order_type == Mt5.ORDER_TYPE_SELL
            or order_type == Mt5.ORDER_TYPE_SELL_LIMIT
            or order_type == Mt5.ORDER_TYPE_SELL_STOP
        ):
            if last_candle.high > trade["sl"]:
                trade_closing = True
                result_trade = "sl"
            elif last_candle.low < trade["tp"]:
                trade_closing = True
                result_trade = "tp"
        return trade_closing, result_trade

    def manage_balance_after_trade_closing(
        self, trade: Dict, result_trade: str, rr: Optional[float]
    ):
        """
        change the balance depending if the trade is SL, TP or BE
        """
        new_balance = None
        if result_trade == "tp":
            new_balance = (
                self.account.balance + self.account.balance * self.risk_percentage * rr
            ) - (
                self.account.balance
                * self.risk_percentage
                * 0.15  # 0.15 simulate the fee of the broker
            )
        elif result_trade == "sl":
            if trade["sl_to_be"]:
                new_balance = self.account.balance - (
                    self.account.balance
                    * self.risk_percentage
                    * 0.15  # 0.15 simulate the fee of the broker even if you are at BE
                )
            else:
                new_balance = (
                    self.account.balance
                    - self.account.balance
                    * (self.risk_percentage * trade["sl_ratio_modified"])
                    - (
                        self.account.balance
                        * self.risk_percentage
                        * 0.15  # 0.15 simulate the fee of the broker
                    )
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

    @staticmethod
    def check_if_trade_sl_to_be(trade: Dict, last_candle: Candle) -> None:
        """
        check if the trade SL need to be put at BE
        """
        if trade["be"] is None:
            return None
        order_type = trade["order_type"]
        if (
            order_type == Mt5.ORDER_TYPE_BUY
            or order_type == Mt5.ORDER_TYPE_BUY_LIMIT
            or order_type == Mt5.ORDER_TYPE_BUY_STOP
        ):
            if last_candle.close >= trade["be"]:
                trade["sl_to_be"] = True
                trade["sl"] = trade["price"]
        elif (
            order_type == Mt5.ORDER_TYPE_SELL
            or order_type == Mt5.ORDER_TYPE_SELL_LIMIT
            or order_type == Mt5.ORDER_TYPE_SELL_STOP
        ):
            if last_candle.close <= trade["be"]:
                trade["sl_to_be"] = True
                trade["sl"] = trade["price"]

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
            if self.strat_auto_manage_trade:
                trade, trade_closing, result_trade = manage_bot(
                        trade, **self.kwargs
                    )
            else:
                trade_closing, result_trade = self.check_if_trade_need_closing(
                    trade, last_candle
                )
            rr = trade["RR"]
            if trade_closing:
                new_balance = self.manage_balance_after_trade_closing(
                    trade, result_trade, rr
                )
                trade = self.check_if_trade_is_win(trade, new_balance)
                self.account.balance = new_balance
                trade["on_going"] = False
                self.trade_on_going = False
            elif not self.strat_auto_manage_trade:
                self.check_if_trade_sl_to_be(trade, last_candle)
            self.manage_drawdown()

    def launch_strategy(self, data_step_to_process: dict[str, pd.DataFrame]):
        """
        launch the strategy and manage result of trades
        """
        data_tf = data_step_to_process[f"TF {self.time_frame}"]
        last_candle = Candle(data_tf.iloc[-1])
        self.kwargs["backtest_data"] = data_step_to_process
        self.manage_on_going_trades(last_candle)
        if not self.trade_on_going or self.more_than_on_trade_on_going:
            trade = bot_strategy(**self.kwargs)
        else:
            trade = None
        if trade is not None:
            if trade["on_going"]:
                self.trade_on_going = True
            if self.delete_previous_pending_trade:
                self.info_all_trade = dict(
                    (key, value)
                    for (key, value) in self.info_all_trade.items()
                    if not value["pending"]
                )
            info_trade_deep_copy = deepcopy(trade)
            self.info_all_trade[
                str(last_candle.date) + str(trade["order_type"])
            ] = info_trade_deep_copy
