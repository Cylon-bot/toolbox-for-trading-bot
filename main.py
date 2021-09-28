import click
from termcolor import colored
from backtest.backtest import create_backtest
from bot_strat import live_trading
from typing import List


@click.command()
@click.option(
    "--action",
    help="action to execute (str) : [backtest, launch_bot]",
)
@click.option(
    "--account_currency",
    default="USD",
    help="account currency used (str), examples : [USD, EUR]",
)
@click.option("--risk", default=0.5, type=float, help="risk used(float) : ")
@click.option(
    "--pair_list",
    multiple=True,
    default=["EURUSD-Z"],
    help="pair used(list) : [EURUSD, GBPUSD]",
)
def main(
    action: str,
    account_currency: str,
    risk: float,
    pair_list: List[str],
    normal_account: bool = True,
):
    """
    launch the specified action
    """
    if action == "launch_bot":
        live_trading(account_currency, risk, pair_list)
    elif action == "backtest":
        create_backtest()
    else:
        print(colored("No action with that name", "red"))


if __name__ == "__main__":
    main()
