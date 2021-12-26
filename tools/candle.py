from typing import List, Optional, Union, Dict

import pandas as pd


__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


class Candle:
    """
    class with all the important information about the candles you use for your strat
    """

    def __init__(
        self,
        candle_info: Union[Dict, pd.DataFrame],
        bollinger_band: bool = False,
        rsi: bool = False,
        minimum_rejection: Optional[float] = None,
        ema_list: Optional[List[int]] = None,
        body_min: Optional[float] = None,
        id_candle: Optional[int] = None,
    ):

        self.ID = id_candle
        self.open = candle_info["open"]
        self.close = candle_info["close"]
        self.high = candle_info["high"]
        self.low = candle_info["low"]
        self.date = candle_info["time"]
        self.body = self.close - self.open
        self.EMAs = self.add_ema_info(candle_info, ema_list)
        self.bullish = self.check_bullish_or_bearish()
        if bollinger_band:
            self.upper_bollinger = candle_info["upper_bollinger"]
            self.middle_bollinger = candle_info["middle_bollinger"]
            self.lower_bollinger = candle_info["lower_bollinger"]
        if rsi:
            self.RSI = candle_info["RSI"]
        pips = 0.0001
        if minimum_rejection is not None:
            minimum_rejection_pips = minimum_rejection * pips
            self.high_rejection, self.low_rejection = self.is_rejection_wicks(
                minimum_rejection_pips
            )
        else:
            self.high_rejection, self.low_rejection = "Unknown", "Unknown"

        if body_min is not None and minimum_rejection is not None:
            body_min_pips = body_min * pips
            self.doji = self.check_doji(body_min_pips)
        else:
            self.doji = "Unknown"

        self.engulfing = "Unknown"

    def check_bullish_or_bearish(self) -> bool:
        """
        check if the candle is bullish or bearish
        """
        if self.close - self.open >= 0:
            return True
        else:
            return False

    @staticmethod
    def add_ema_info(
        candle_info: pd.DataFrame, ema_list: Optional[List[int]]
    ) -> Optional[dict[int, any]]:
        """
        add the info of the EMA to the candle
        """
        emas = dict()
        if ema_list is None:
            return None
        for ema in ema_list:
            emas[ema] = candle_info[f"EMA{str(ema)}"]
        return emas

    def check_engulfing(self, previous_candle: "Candle"):
        """
        check if the candle is an engulfing candle
        """
        if self.bullish and not previous_candle.bullish:
            if self.close > previous_candle.high:
                self.engulfing = True
            else:
                self.engulfing = False
        elif not self.bullish and previous_candle.bullish:
            if self.close < previous_candle.low:
                self.engulfing = True
            else:
                self.engulfing = False
        else:
            self.engulfing = False

    def check_doji(self, body_min) -> Optional[bool]:
        """
        check if the candle is a doji, need a body min parameter
        """
        if (
            self.high_rejection == "Unknown"
            or self.low_rejection == "Unknown"
            or self.body == "Unknown"
        ):
            return None
        if (self.high_rejection or self.low_rejection) and abs(self.body) <= body_min:
            return True
        else:
            return False

    def is_rejection_wicks(self, minimum_rejection: float) -> (bool, bool):
        """
        check if the wicks are rejection wicks, need minimum rejection parameter
        """
        if self.bullish:
            if (
                self.high - self.close > minimum_rejection
                and self.open - self.low > minimum_rejection
            ):
                return True, True
            elif self.high - self.close > minimum_rejection > self.open - self.low:
                return True, False
            elif self.high - self.close < minimum_rejection < self.open - self.low:
                return False, True
            else:
                return False, False
        if not self.bullish:
            if (
                self.high - self.open > minimum_rejection
                and self.close - self.low > minimum_rejection
            ):
                return True, True
            elif self.high - self.open > minimum_rejection > self.close - self.low:
                return True, False
            elif self.high - self.open < minimum_rejection < self.close - self.low:
                return False, True
            else:
                return False, False

    def print_details(self, print_message: bool = False):
        """
        print all the details of the candle for the user --> need refactoring (use __str__ instead)
        """
        pips = 0.0001
        pips_inverse = 1 / pips
        message = (
            f"Candle: {self.date}\n"
            f"Open: {self.open}\n"
            f"Close: {self.close}\n"
            f"High: {self.high}\n"
            f"Low: {self.low}\n"
            f"body: {round(self.body*pips_inverse,2)} Pips\n"
            f"doji: {self.doji}\n"
            f"EMA: {self.EMAs}\n"
            f"Bullish: {self.bullish}\n"
            f"Engulfing: {self.engulfing}\n"
            f"High_rejection: {self.high_rejection}\n"
            f"Low_rejection: {self.low_rejection}\n"
            f'{"."*50}'
        )
        if print_message:
            print(message)
        return message


def rebuild_candle(candles_workers: pd.DataFrame):
    built_candle_dict = {"close": candles_workers["close"].iloc[-1]}
    for number_candle, candle in enumerate(candles_workers.iloc()):
        if number_candle == 0:
            built_candle_dict["high"] = candle["high"]
            built_candle_dict["low"] = candle["low"]
            built_candle_dict["open"] = candle["open"]
            built_candle_dict["time"] = candle["time"]
        else:
            if candle["high"] > built_candle_dict["high"]:
                built_candle_dict["high"] = candle["high"]
            if candle["low"] < built_candle_dict["low"]:
                built_candle_dict["low"] = candle["low"]
    built_candle = Candle(built_candle_dict)
    return built_candle