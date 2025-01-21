from lib.ahoi.modem.modem import Modem
import sys
from src.NodeTDAMAC import NodeTDAMAC
from src.GatewayTDAMAC import GatewayTDAMAC

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(f"Usage: python3 {sys.argv[0]} <serialport> <gateway_id> nodes...")
        sys.exit(1)
    modemGateway = Modem()
    modemGateway.connect(sys.argv[1])
    modemGateway.receive(True)
    modemGateway.transducer(5)
    modemGateway.txGain(10)
    gateway = GatewayTDAMAC(modemGateway, list(map(int,sys.argv[3:])), nbReqMax=10)
    gateway.gatewayId = int(sys.argv[2])
    # test
    gateway.run()

