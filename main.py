import click
from termcolor import colored

from bot_strat import live_trading
from typing import List

try:
    from backtest.my_personal_backtest import create_personal_backtest as create_backtest
except ImportError:
    from backtest.backtest import create_backtest

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


@click.command()
@click.option(
    "--action",
    help="action to execute (str) : [backtest, launch_bot]",
)
@click.option(
    "--account_currency",
    help="account currency used (str), examples : USD",
)
@click.option("--risk", type=float, help="risk used(float)")
@click.option(
    "-s",
    "--symbols",
    multiple=True,
    help="symbols used(list) : -s EURUSD -s GBPUSD...",
)
def main(
    action: str,
    account_currency: str,
    risk: float,
    symbols: List[str],
):
    """
    launch the specified action
    """
    if action == "launch_bot":
        if account_currency is None or risk is None or symbols is None:
            print(
                "You need to give us input.\naccount_currency\nrisk\nsymbols\n--help for help"
            )
            return None

        live_trading(account_currency, risk, symbols)
    elif action == "backtest":
        create_backtest()
    else:
        print(colored("No action with that name", "red"))


if __name__ == "__main__":
    main()
