from datetime import datetime
from enum import Enum
from lib.ahoi.modem.packet import packet2HexString
import string
import os 
from datetime import datetime
import time

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


LOGLEVELS = Enum('LOGLEVELS', [('DEBUG', bcolors.OKCYAN), ('INFO',bcolors.OKBLUE), ('WARNING', bcolors.WARNING), ('ERROR', bcolors.FAIL)])


class Logger:
    def __init__(self, title: str):
        self.title = title
        self.logname = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def __print(self, level: LOGLEVELS, text: str, *args, **kwargs):
        now = datetime.now()

        print(f"{level.value}{now.strftime('%Y-%m-%d %H:%M:%S')} [{self.title}] {level.name}:{bcolors.ENDC} {text}", *args, **kwargs)

    def logTX(self, pkt, name: str = ""):
        output = "TX@"
        output += "{:.3f}".format(time.time())
        output += " "
        output += packet2HexString(pkt)

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/{name}-{self.logname}.log", "a") as f:
            f.write(output + "\n")

    def logRX(self, pkt, name: str = ""):
        output = "RX@"
        output += "{:.3f}".format(time.time())
        output += " "
        output += packet2HexString(pkt)
        output += "("
        output += "".join(
            filter(
                lambda x: x
                in string.digits + string.ascii_letters + string.punctuation,
                pkt.payload.decode("ascii", "ignore"),
            )
        )
        output += ")"

        os.makedirs("logs", exist_ok=True)
        with open(f"logs/{name}-{self.logname}.log", "a") as f:
            f.write(output + "\n")

    def debug(self, text: str, *args, **kwargs):
        self.__print(LOGLEVELS.DEBUG, text, *args, **kwargs)

    def info(self, text: str, *args, **kwargs):
        self.__print(LOGLEVELS.INFO, text, *args, **kwargs)
    
    def warning(self, text: str, *args, **kwargs):
        self.__print(LOGLEVELS.WARNING, text, *args, **kwargs)
    
    def error(self, text: str, *args, **kwargs):
        self.__print(LOGLEVELS.ERROR, text, *args, **kwargs)

    def log(self, level: LOGLEVELS, text: str, *args, **kwargs):
        self.__print(level, text, *args, **kwargs)