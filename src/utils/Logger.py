from datetime import datetime
from enum import Enum

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

    def __print(self, level: LOGLEVELS, text: str, *args, **kwargs):
        now = datetime.now()
        print(f"{level.value}{now.strftime('%Y-%m-%d %H:%M:%S')} [{self.title}] {level.name}:{bcolors.ENDC} {text}", *args, **kwargs)

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