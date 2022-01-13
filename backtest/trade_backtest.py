from typing import Optional

from pydantic import BaseModel


class TradeBacktest(BaseModel):
    order_type: int
    date_entry: str
    price: float
    rr: float
    be: Optional[float]
    sl: float
    tp: float
    pending: bool
    on_going: bool
    sl_to_be: bool = False
    sl_ratio_modified: int = 1
    win: Optional[bool] = None
    comment: Optional[str] = None
