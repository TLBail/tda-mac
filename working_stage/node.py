from lib.ahoi.modem.modem import Modem
from src.NodeTDAMAC import NodeTDAMAC
import sys


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"Usage: python3 {sys.argv[0]} <serialport> <modem_id> <gateway_id>")
        sys.exit(1)

    modem = Modem()
    modem.connect(sys.argv[1])
    modem.receive(True)
    
    node = NodeTDAMAC(modem, int(sys.argv[2]), int(sys.argv[3]))
