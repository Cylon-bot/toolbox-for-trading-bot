import click
from termcolor import colored
from backtest.backtest import launch_backtest
from strat_bot import live_trading
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
@click.option(
    "--normal_account",
    default=True,
    help="normal account(bool), if you trade at admiral market, you need to specifie False",
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
        live_trading(account_currency, risk, pair_list, normal_account)
    elif action == "backtest":
        launch_backtest()
    else:
        print(colored("No action with that name", "red"))


if __name__ == "__main__":
    main()
