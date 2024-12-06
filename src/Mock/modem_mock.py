from src.i_modem import IModem
from lib.ahoi.modem.packet import makePacket
class ModemMock(IModem):
    def __init__(self, nodes):
        self.connected = False
        self.callbacks = []
        self.nodes = nodes

    def connect(self, connection):
        print(f"Mock: Connected to {connection}")
        self.connected = True

    def addRxCallback(self, callback):
        self.callbacks.append(callback)
        print(f"Mock: Added callback {callback}")

    def removeRxCallback(self, cb):
        """Remove a function to be called on rx pkt."""
        if cb in self.callbacks:
            self.callbacks.remove(cb)

    def send(self, dst, src, type, payload=bytearray(), status=None, dsn=None):
        pkt = makePacket(src, dst, type, status, dsn, payload)
        if not self.connected:
            raise Exception("Modem not connected")
        print(f"Mock: Sent packet to {dst} with payload {payload}")
        for node in self.nodes:
            if node.adress == dst or dst == 255:
                node.receive(pkt)

    def simulateRx(self, packet):
        for callback in self.callbacks:
            callback(packet)

    

