from typing import Optional

import MetaTrader5 as Mt5
from pandas import DataFrame
from termcolor import colored

from account import Account
from tools.tools_trade import (
    calc_position_size_forex,
    get_order_history,
    positions_get,
)

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


class Trade:
    """
    class use to manage all different type of market order on your mt5 account
    """

    def __init__(
        self,
        symbol: str,
        order_type: int,
        price: float = None,
        tp: float = None,
        sl: float = None,
        magic_number: int = 42000,
        comment: str = "trade from robot",
    ):
        self.size = None
        self.symbol = symbol
        self.order_type = order_type
        self.price = price
        self.tp = tp
        self.sl = sl
        self.result_open_request = None
        self.ticket_order = None
        if order_type == Mt5.ORDER_TYPE_BUY_LIMIT:
            self.action = Mt5.TRADE_ACTION_PENDING
            print(f"trying to set a buy limit trade on {self.symbol}!")
        elif order_type == Mt5.ORDER_TYPE_SELL_LIMIT:
            self.action = Mt5.TRADE_ACTION_PENDING
            print(f"trying to set a sell limit trade on {self.symbol}!")
        elif order_type == Mt5.ORDER_TYPE_BUY:
            self.action = Mt5.TRADE_ACTION_DEAL
            print(f"trying to set a direct buy trade on {self.symbol}!")
        elif order_type == Mt5.ORDER_TYPE_SELL:
            self.action = Mt5.TRADE_ACTION_DEAL
            print(f"trying to set a direct sell trade on {self.symbol}!")
        elif order_type == Mt5.ORDER_TYPE_BUY_STOP:
            self.action = Mt5.TRADE_ACTION_PENDING
            print(f"trying to set a buy stop trade on {self.symbol}!")
        elif order_type == Mt5.ORDER_TYPE_SELL_STOP:
            self.action = Mt5.TRADE_ACTION_PENDING
            print(f"trying to set a sell stop trade on {self.symbol}!")
        else:
            print("cannot proceed, unrecognized order type")
        self.request_open = {
            "action": self.action,
            "symbol": symbol,
            "type": order_type,
            "price": price,
            "magic": magic_number,
            "comment": comment,
            "type_time": Mt5.ORDER_TIME_GTC,
            "type_filling": Mt5.ORDER_FILLING_FOK,
        }
        if tp is not None:
            self.request_open["tp"] = tp
        if sl is not None:
            self.request_open["sl"] = sl

    def open_position(
        self,
        my_account: Account,
        account_currency: Optional[str] = None,
        risk: Optional[float] = None,
        account_currency_conversion: Optional[DataFrame] = None,
        size: Optional[float] = None,
        close_previous_pending_order: Optional[bool] = False,
    ) -> (bool, any):
        """
        use to open a market order on the given symbol
        this market order can be :
            - direct sell
            - direct buy
            - buy limit
            - sell limit
            - buy stop
            - sell stop
        """

        symbol_info = Mt5.symbol_info(self.symbol)
        symbol_is_real = self.check_symbol(symbol_info, self.symbol)
        if not symbol_is_real:
            return False, None

        if self.action == Mt5.TRADE_ACTION_PENDING and self.price is None:
            print("You need to give a price for a pending order")
            return None
        if self.action == Mt5.TRADE_ACTION_DEAL:
            self.finding_actual_price()
            self.request_open["deviation"] = 20

        if size is None:
            self.request_open["volume"] = self.finding_size(
                account_currency, risk, account_currency_conversion
            )
        else:
            self.request_open["volume"] = size

        self.result_open_request = Mt5.order_send(self.request_open)
        iterator = 0
        while (
            self.result_open_request.comment == "Requote"
            or (self.result_open_request.comment == "Invalid price")
            or (self.result_open_request.comment == "No prices")
            or (self.result_open_request.comment == "Invalid volume")
        ) and iterator < 50:
            self.finding_actual_price()

            if size is None:
                self.request_open["volume"] = self.finding_size(
                    account_currency, risk, account_currency_conversion
                )
            else:
                self.request_open["volume"] = size

            self.result_open_request = Mt5.order_send(self.request_open)
            iterator += 1
        if self.result_open_request.retcode != Mt5.TRADE_RETCODE_DONE:
            print(
                f"Failed to send order :(, retcode: {self.result_open_request.retcode}"
            )
            print(colored(self.result_open_request, "blue"))
            return False, self.result_open_request
        else:
            self.ticket_order = self.result_open_request.order
            print(colored("Order successfully placed!", "green"))
            for ticket_order_pending, trade_pending in my_account.trade_pending.items():

                if trade_pending.symbol == self.symbol and close_previous_pending_order:
                    print(
                        f"close previous pending order on {self.symbol} with ticket order {ticket_order_pending}"
                    )
                    trade_pending.close_position(my_account)
                    break

            if self.request_open["action"] == Mt5.TRADE_ACTION_PENDING:
                my_account.trade_pending[self.ticket_order] = self
            if self.request_open["action"] == Mt5.TRADE_ACTION_DEAL:
                my_account.trade_on_going[self.ticket_order] = self

            return True, self.result_open_request

    def finding_actual_price(self):
        """
        in case of a direct order, we need to find the actual price which is the purpose of this function
        """
        if self.order_type == Mt5.ORDER_TYPE_BUY:
            self.price = Mt5.symbol_info_tick(self.symbol).ask
            self.request_open["price"] = self.price
        elif self.order_type == Mt5.ORDER_TYPE_SELL:
            self.price = Mt5.symbol_info_tick(self.symbol).bid
            self.request_open["price"] = self.price

    def finding_size(
        self,
        account_currency: str,
        risk: float,
        account_currency_conversion,
    ) -> float:
        """
        in case of the size not specified by the user, we need to find the lot size of the order
        thanks to the stop loss and the risk which is the purpose of this function
        """

        difference_sl_price = abs(self.sl - self.price)
        volume = calc_position_size_forex(
            self.symbol,
            account_currency,
            risk,
            difference_sl_price,
            account_currency_conversion,
        )
        return volume

    @staticmethod
    def check_symbol(symbol_info: Mt5.SymbolInfo, symbol: str):
        """
        check if the symbol given by the user exist in the broker trading list
        """
        if symbol_info is None:
            print(symbol, "not found")
            return False

        if not symbol_info.visible:
            print(symbol, "is not visible, trying to switch on")
            if not Mt5.symbol_select(symbol, True):
                print("symbol_select({}}) failed, exit", symbol)
                return False
        return True

    def check_moving_trade(self, my_account: Account):
        """
        check if the pending trades has been proc and if on going trades has been closed
        and specify it in the my_account object inside the attribute :
            - my_account.trade_on_going
            - my_account.trade_pending
        -
        """
        history_trade = get_order_history()
        all_trade_on_going = positions_get()

        if all_trade_on_going.empty:
            all_ticket_on_going_trade = ["No trade"]
        else:
            all_ticket_on_going_trade = list(all_trade_on_going["ticket"].iloc[:])

        if history_trade.empty:
            all_ticket_history_trade = ["No trade"]
        else:
            all_ticket_history_trade = list(history_trade["order"].iloc[:])

        if self.ticket_order in all_ticket_history_trade:

            if self.ticket_order in my_account.trade_on_going:
                del my_account.trade_on_going[self.ticket_order]
            if self.ticket_order in my_account.trade_pending:
                del my_account.trade_pending[self.ticket_order]

        if self.ticket_order in all_ticket_on_going_trade:
            if self.ticket_order in my_account.trade_pending:
                del my_account.trade_pending[self.ticket_order]
                my_account.trade_on_going[self.ticket_order] = self

    def close_position(self, my_account: Account) -> bool:
        """
        close a position either pending or in going
        """
        self.check_moving_trade(my_account)
        order_type_close = None
        price_close = None
        if self.ticket_order in my_account.trade_pending:

            close_request = {
                "action": Mt5.TRADE_ACTION_REMOVE,
                "order": self.ticket_order,
                "magic": 234000,
                "comment": "Close trade",
            }
        elif self.ticket_order in my_account.trade_on_going:

            if (
                self.order_type == Mt5.ORDER_TYPE_BUY
                or self.order_type == Mt5.ORDER_TYPE_BUY_STOP
                or self.order_type == Mt5.ORDER_TYPE_BUY_LIMIT
            ):
                order_type_close = Mt5.ORDER_TYPE_SELL
                price_close = Mt5.symbol_info_tick(self.symbol).bid
            elif (
                self.order_type == Mt5.ORDER_TYPE_SELL
                or self.order_type == Mt5.ORDER_TYPE_SELL_STOP
                or self.order_type == Mt5.ORDER_TYPE_SELL_LIMIT
            ):
                order_type_close = Mt5.ORDER_TYPE_BUY
                price_close = Mt5.symbol_info_tick(self.symbol).ask
            close_request = {
                "action": Mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": self.size,
                "type": order_type_close,
                "position": self.ticket_order,
                "price": price_close,
                "magic": 234000,
                "comment": "Close trade",
                "type_time": Mt5.ORDER_TIME_GTC,
                "type_filling": Mt5.ORDER_FILLING_FOK,
            }
        else:
            print(
                "This order is no longer on pending or on going so cannot proceed to close"
            )
            return False

        result_close_request = Mt5.order_send(close_request)
        while (
            result_close_request.comment == "Requote"
            and self.request_open["action"] == Mt5.TRADE_ACTION_DEAL
        ):
            if (
                self.order_type == Mt5.ORDER_TYPE_BUY
                or self.order_type == Mt5.ORDER_TYPE_BUY_STOP
                or self.order_type == Mt5.ORDER_TYPE_BUY_LIMIT
            ):
                price_close = Mt5.symbol_info_tick(self.symbol).bid
                close_request["price"] = price_close
            elif (
                self.order_type == Mt5.ORDER_TYPE_SELL
                or self.order_type == Mt5.ORDER_TYPE_SELL_STOP
                or self.order_type == Mt5.ORDER_TYPE_SELL_LIMIT
            ):
                price_close = Mt5.symbol_info_tick(self.symbol).ask
                close_request["price"] = price_close
            result_close_request = Mt5.order_send(close_request)

        if result_close_request.retcode != Mt5.TRADE_RETCODE_DONE:
            print(result_close_request)
            print("Failed to close order :(")
            return False
        else:
            print("Order successfully closed!")
            if close_request["action"] == Mt5.TRADE_ACTION_REMOVE:
                del my_account.trade_pending[self.ticket_order]
            if close_request["action"] == Mt5.TRADE_ACTION_DEAL:
                del my_account.trade_on_going[self.ticket_order]
            return True
