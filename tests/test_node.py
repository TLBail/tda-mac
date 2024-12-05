import unittest
from src.i_modem import IModem
from src.modem_mock import ModemMock
from src.modem import Modem

def connectModem(modem: IModem) -> None:
    modem.connect("COM1")

class TestModem(unittest.TestCase):
    def setUp(self):
        self.modem = ModemMock([])


if __name__ == '__main__':
    unittest.main()