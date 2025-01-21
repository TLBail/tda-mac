from src.i_modem import IModem
from lib.ahoi.modem.packet import makePacket
from src.constantes import BROCAST_ADDRESS
class ModemMockGateway(IModem):
    def __init__(self):
        self.connected = False
        self.callbacks = []
        self.nodes: {} = {}
        self.isReceiving = False

    def connect(self, connection):
        self.connected = True


    def receive(self, thread=False):
        self.isReceiving = True
        pass

    def addRxCallback(self, callback):
        self.callbacks.append(callback)

    def removeRxCallback(self, cb):
        """Remove a function to be called on rx pkt."""
        if cb in self.callbacks:
            self.callbacks.remove(cb)

    def send(self, src, dst, type, payload=bytearray(), status=None, dsn=None):
        pkt = makePacket(src, dst, type, status, dsn, payload)
        if not self.connected:
            raise Exception("Modem not connected")
        print(f"Mock: Sending packet to {dst} with payload {payload}")
        if dst == BROCAST_ADDRESS:
            for node in self.nodes.values():
                node.receive(pkt)
        else:
            self.nodes[dst].receive(pkt)

    def simulateRx(self, packet):
        if not self.isReceiving:
            raise Exception("Modem not receiving")
        for callback in self.callbacks:
            callback(packet)

    def addNode(self, node):
        self.nodes[node.adress] = node