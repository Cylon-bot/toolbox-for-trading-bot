# toolbox-for-trading-bot

## Description of the project

this is a toolbox for trading bots in python.

The goal is to provide a code containing a lot of tools to make easier the creation of trading bots in python, meaning not have to bother with how to connect with mt5, take, close and manage a trade, create a backtest...

<span style="color:red">WARNING: THIS PROJECT DOESN'T WORK FOR NOW!!! Therefore, it provides a lot of great tools for creating your own trading bot, 
so it could help you anyway but keep in mind that the project is not working yet. I will remove this warning when the project
will work.</span>.
## Requirements

For all libraries used you have the <requirement.txt> file at your disposal. I used Python3.9 for this project but versions under this one would probably work fine too.

Unfortunately, this project only works on Windows because the mt5 libraries only exists on this distribution. So until they create an API on Linux you will need to use this app and install MetaTrader5 on Windows.

## Tutorial

### Before anything else

The first thing I recommend you to do is to understand how the different modules works together. 

first you will need to do several things : 

- Install Python>3.9 and pip --> can't be sure if the program works below 3.9

- Install the software MetaTrader5 

- Install all dependencies needed.You can find all the dependencies inside the file <requirement.txt>. In order to install them : <python -m pip install -r requirement.txt> 
PS : if you have trouble to install ta-lib you will need to install the wheel here: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
- Create a demo account on MetaTrader5 and store the info in a file <demo_account_test.yaml> at the root of the project. The format of this file need to be like : 

Name     : Slim Shady <br/>
Type     : Forex Hedged USD <br/>
Server   : MetaQuotes-Demo <br/>
Login    : 4242424242 <br/>
Password : IamAVeryHardPasswordToCrack <br/>
Investor : Null <br/>

### How can You use it


you normally have to modify just 2 things : 

- the file <bot_strat.py>

- the function <create_backtest> inside the file </backtest/backtest.py>

the function <create_backtest> will be there to launch a backtest of your strategy, and you will use the file <bot_strat.py> to write your own bot. There is of course an example of a strategy inside the file <bot_strat.py> and the function <create_backtest> is functional with it.


### Launch the program

You can launch 2 things in the code : 

- Your bot for live trading 

- The backtest of your bot

In order to backtest your bot you need to write at the root of the project in a command line : 

<python .\main.py --action=backtest>

You can test right away the backtest with the strat already implemented in the program (caution : This strat is not profitable, this is only an example for you)

In order to launch the bot in a live trading session you need to write at the root of the project in a command line : 

<py .\main.py --action=launch_bot --account_currency=USD --risk=0.5 --symbols EURUSD >

- the account currency can be replaced by another currency

- the risk can be replaced by any risk (but the volume cannot exceed the marge given by your broker)

- the symbol can be replaced by any other forex symbol (index, share and crypto is coming later). if you want to launch your bot on several symbols at the same time, juste write for instance : 

<py .\main.py --action=launch_bot --account_currency=USD --risk=0.5 -s EURUSD -s NZDUSD -s GBPUSD>

