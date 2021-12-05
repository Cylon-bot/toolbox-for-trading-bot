import MetaTrader5 as Mt5
from pathlib import Path
from backtest.backtest import Backtest
from termcolor import colored

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


def create_personal_backtest():
    """
    create your backtest here, you have an example
    with the bot_strat already implemented
    """

    # Modify this part
    ##############################################################
    all_symbol_backtest = ["EURUSD"]
    all_period_backtest = [
        "September_2021",
        "August_2021",
        "July_2021",
        "June_2021",
        "May_2021",
        "April_2021",
        "March_2021",
        "February_2021",
        "January_2021",
        "December_2020",
        "November_2020",
    ]
    name_strat = "Bollinger"
    risk = 0.5
    all_file_data = [
        "September_2021.txt",
        "August_2021.txt",
        "July_2021.txt",
        "June_2021.txt",
        "May_2021.txt",
        "April_2021.txt",
        "March_2021.txt",
        "February_2021.txt",
        "January_2021.txt",
        "December_2020.txt",
        "November_2020.txt",
    ]
    initial_account_balance = 100_000
    time_frame = Mt5.TIMEFRAME_M1
    more_than_on_trade_on_going = False
    delete_previous_pending_trade = False
    strat_auto_manage_trade = True
    interval_hour_list = [
        (9, 19),
        (9, 10),
        (10, 11),
        (11, 12),
        (12, 13),
        (13, 14),
        (14, 15),
        (15, 16),
        (16, 17),
        (17, 18),
        (18, 19),
    ]
    # here you need to create a dictionary with the name of the
    # parameters in your strat function as key and input as value
    # you don't have to put the parameters inside kwargs if they
    # are already initialized and you don't want to change them
    # example : I don't put the parameter my_account because I
    # want the initialized value None
    # don't put backtest_data parameter, it will be automatically
    # fill by the backest class (PS : don't rename this parameter)
    for symbol in all_symbol_backtest:
        for interval in interval_hour_list:
            all_balance = 0
            all_max_drawdown_percentage = 0
            for iterator, period_backtest in enumerate(all_period_backtest):
                unique_id_backtest = period_backtest + str(interval) + symbol
                kwargs = {
                    "symbol": symbol,
                    "risk": risk,
                    "bollinger_band": True,
                    "RSI": True,
                    "interval_hour": interval,
                }

                # Normally you don't have to modify this part
                ##############################################################
                my_backtest = Backtest(
                    symbol,
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
                    / "my_personal_data_candles"
                    / symbol
                    / all_file_data[iterator]
                )
                balance, max_drawdown_percentage = my_backtest.launch_backtest(
                    path_data
                )
                all_balance += balance
                all_max_drawdown_percentage += max_drawdown_percentage
            mean_balance = all_balance / len(all_period_backtest)
            mean_balance_percentage = (
                (mean_balance - initial_account_balance) / initial_account_balance
            ) * 100
            mean_max_drawdown_percentage = all_max_drawdown_percentage / len(
                all_period_backtest
            )
            ratio_balance_dd = mean_balance_percentage / mean_max_drawdown_percentage
            message = (
                f"The ratio balance/DD on the backtest with interval = {interval} is : {ratio_balance_dd}"
                f"\n{'-'*100}\n\n"
            )
            print(colored(message, "green"))
            with open(
                f"backtest/backtest_by_symbol/{symbol}/{name_strat}.txt", "a"
            ) as text_file:
                text_file.write(message)
