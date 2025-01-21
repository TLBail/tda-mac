from lib.ahoi.modem.modem import Modem
from src.NodeTDAMAC import NodeTDAMAC
import sys


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
        userInput = input("Enter a message to send to the gateway or 'exit' to quit :")
        if userInput == 'exit':
            break

        # verify if the message converted to bytearray is not to big
        try:
            maxSize = node.dataPacketOctetSize
            payload = bytearray(userInput, 'utf-8')
            if len(payload) > maxSize:
                print(f"Payload is too big, max size is {maxSize}")
            else:
                node.setReponsePayload(payload)
        except Exception as e:
            print(f"Error: {e}")

