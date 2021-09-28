# toolbox-for-trading-bot

## Description of the project

this is a toolbox for trading bots in python.

The goal is to provide a code containing a lot of tools to make easier the creation of trading bots in python, meaning not have to bother with how to connect with mt5, take, close and manage a trade, create a backtest...

## Requirements

For all libraries used you have the requirement.txt file at your disposal. I used Python3.9 for this project but versions under this one would probably works fine too.

Unfortunately, this project only works on windows because the mt5 librarie only exists on this distribution. So until they create an API on Linux you will need to use and install MetaTrader5 on windows.

## Tutorial

The first thing I recommend you to do is to understand how the differents modules works together. 

you normally have to modify just 2 things : 

	- the file bot_strat.py

	- the function create_backtest inside the file /backtest/backtest.py

the function create_backtest will be there to launch a backtest of your strategy and you will use the file bot_strat.py to write your own bot. There is of course an example of a strategy inside the file bot_strat.py and the function create_backtest is functional with it.

