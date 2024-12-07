from src.i_modem import IModem
from lib.ahoi.modem.packet import makePacket
from src.constantes import GATEWAY_ID
from src.Mock.modem_mock_gateway import ModemMockGateway
from src.Mock.node_mock_gateway import NodeMockGateway
class ModemMockNode(IModem):
    def __init__(self, address, gatewayModem=None):
        self.connected = False
        self.callbacks = []
        self.transmitDelay = 0
        self.receptionDelay = 0
        self.address = address

        # Create a mock gateway if none is provided
        if gatewayModem is None:
            self.gatewayModem = ModemMockGateway()
            self.gatewayModem.connected = True
            def onNodeMockReceive(node, packet):
                self.simulateRx(packet)

            self.node = NodeMockGateway(self.gatewayModem, 1, onNodeMockReceive)
            self.node.transmitDelay = 1
            self.node.receptionDelay = 1
            self.gatewayModem.addNode(self.node)
        else:
            self.gatewayModem = gatewayModem

    def connect(self, connection):
        print(f"Modem Mock Node: Connected to {connection}")
        self.connected = True
    def addRxCallback(self, callback):
        self.callbacks.append(callback)
        print(f"Modem Mock Node: Added callback {callback}")

    def removeRxCallback(self, cb):
        """Remove a function to be called on rx pkt."""
        if cb in self.callbacks:
            self.callbacks.remove(cb)

    def send(self, dst, src, type, payload=bytearray(), status=None, dsn=None):
        if dst != GATEWAY_ID:
            raise Exception("Mock: Destination must be the gateway")
        pkt = makePacket(src, dst, type, status, dsn, payload)
        if not self.connected:
            raise Exception("Modem not connected")
        print(f"Mock: Send packet to {dst} with payload {payload}")
        self.gatewayModem.nodes[src].transmit(pkt)
    def simulateRx(self, packet):
        for callback in self.callbacks:
            callback(packet)
