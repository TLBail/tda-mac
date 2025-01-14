from lib.ahoi.modem.modem import Modem
from src.NodeTDAMAC import NodeTDAMAC
from src.GatewayTDAMAC import GatewayTDAMAC

if __name__ == '__main__':
    modemGateway = Modem()
    modemGateway.connect("COM6")
    modemGateway.receive(True)
    gateway = GatewayTDAMAC(modemGateway, [84])
    # test
    gateway.run()

