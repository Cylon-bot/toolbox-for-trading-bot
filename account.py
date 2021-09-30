import MetaTrader5 as mt5
import yaml
from pathlib import Path

__author__ = "Thibault Delrieu"
__copyright__ = "Copyright 2021, Thibault Delrieu"
__license__ = "MIT"
__maintainer__ = "Thibault Delrieu"
__email__ = "thibault.delrieu.pro@gmail.com"
__status__ = "Production"


class Account:
    """
    needed for connecting with the mt5 account
    """

    def __init__(
        self,
        account_currency: str = "USD",
        original_risk: float = 1,
    ):

        self.get_account_info()
        self.trade_open = False
        self.trade_on_going = {}
        self.trade_pending = {}
        self.account_currency = account_currency
        self.original_risk = original_risk

    def connect(self, credential: str = "demo_account.yaml"):
        """
        input --> yaml file path from project root with credential in it
        exemple of a valid input file :
        ##########
        Name     : Slim Shady
        Type     : Forex Hedged USD
        Server   : MetaQuotes-Demo
        Login    : 4242424242
        Password : IamAVeryHardPasswordToCrack
        Investor : Null
        ##########
        In fact this function only need login, password, server and name
        but this is the file format given by mt5 when you create a demo account
        """
        ABSOLUTE_PATH_LAUNCH = Path.cwd()
        DEMO_ACCOUNT_CREDENTIAL_PATH = ABSOLUTE_PATH_LAUNCH / credential
        with open(DEMO_ACCOUNT_CREDENTIAL_PATH) as credential_file:
            DATA_CREDENTIAL_FILE = yaml.load(credential_file, Loader=yaml.FullLoader)
        self.id_account = DATA_CREDENTIAL_FILE["Login"]
        self.psw_account = DATA_CREDENTIAL_FILE["Password"]
        self.server_account = DATA_CREDENTIAL_FILE["Server"]
        self.account_owner = DATA_CREDENTIAL_FILE["Name"]
        mt5.initialize()
        authorized = mt5.login(self.id_account, self.psw_account, self.server_account)
        if authorized:
            print("Connected: Connecting to MT5 Client with account :\n")
            print(f"Account owner : {self.account_owner}")
            print(f"ID account : {self.id_account}")
            print(f"Server : {self.server_account}")
            return 0
        else:
            print(
                "Failed to connect at account #{}, error code: {}".format(
                    self.id_account, mt5.last_error()
                )
            )
            return 1

    def get_account_info(self):
        self.account_info = mt5.account_info()


class AccountSingleton:
    """
    needed for async functions who uses the class account in order
    to not have 2 functions accessing the class at the same time
    """

    def __init__(self):
        self.account = None

    def set(self, acc: Account):
        if not self.account:
            self.account = acc
        else:
            raise RuntimeError("Singleton already set")

    def get(self) -> Account:
        if self.account:
            return self.account
        else:
            raise RuntimeError("Singleton unset")

    async def get_async(self) -> Account:
        if self.account:
            return self.account
        else:
            raise RuntimeError("Singleton unset")
