# toolbox-for-trading-bot

## Description of the project

this is a toolbox for trading bot in python.

The goal is to provide a code containing a lot of tools to make easier the creation of trading bot in python, meaning not have to bother with how to connect with mt5, take, close and manage a trade, create a backtest...

## Tutorial

The first thing I recomand you to do is to understand how the different module works together. 

you normally have to modify just 2 things : 

	- the file bot_strat.py

	- the function create_backtest inside the file /backtest/backtest.py

the function create_backtest will be here to launch a backtest of your strategy and you will use the file bot_strat.py to write your own bot. There is of course an example of a strategy inside the file bot_strat.py and the function create_backtest is functionnal with it.

