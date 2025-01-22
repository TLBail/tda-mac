from lib.ahoi.modem.modem import Modem
from src.NodeTDAMAC import NodeTDAMAC
import sys
from datetime import datetime
import time


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"Usage: python3 {sys.argv[0]} <serialport> <modem_id> <gateway_id>")
        sys.exit(1)

    modem = Modem()
    modem.transducer(5)
    modem.txGain(10)
    modem.connect(sys.argv[1])
    modem.receive(True)

    # run tdamac
    node = NodeTDAMAC(modem, int(sys.argv[2]), int(sys.argv[3]))

    while True:
        # Récupération de l'heure actuelle au format HH:MM
        new_time = datetime.now().strftime("%H:%M")
        node.setReponsePayload(bytearray(new_time, 'utf-8'))
        time.sleep(1)