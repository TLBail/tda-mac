from src.Mock.modem_mock_gateway import ModemMockGateway
import time
import threading
from lib.ahoi.modem.packet import makePacket
from src.constantes import FLAG_R


def ResponseWithAckForDelay(node, delay):
    """payload is the full time of flight because ModemMock does not simulate time of flight"""
    tof = int((node.receptionDelay + node.transmitDelay) * 1e6)
    tof_payload = tof.to_bytes(4, 'big')
    ack_packet = makePacket(
        src=node.adress,
        dst=0,
        type=0x7F,  # Type pour les ACK de ranging
        payload=tof_payload
    )
    node.transmit(ack_packet)
class NodeMockGateway:

    def __init__(self, modem: ModemMockGateway, adress, onReceive=None):
        self.modem = modem
        self.adress = adress
        self.onReceive = onReceive
        self.receivePackets = []
        self.transmitDelay = 0
        self.receptionDelay = 0
        self.looseReceivePacket = False
        self.looseTransmitPacket = False
        self.looseNbReceivePacket = 0
        self.looseNbTransmitPacket = 0

    def transmit(self, packet):
        if(self.looseNbTransmitPacket > 0):
            self.looseNbTransmitPacket -= 1
            print(f"Mock: Node {self.adress} lost packet while transmitting")
            return
        if(self.looseTransmitPacket):
            print(f"Mock: Node {self.adress} lost packet while transmitting")
            return
        def asyncTransmit():
            print(f"Mock: Node {self.adress} is transmitting packet")
            time.sleep(self.transmitDelay)
            print(f"Mock: Node {self.adress} transmitted packet")
            self.modem.simulateRx(packet)

        threading.Thread(target=asyncTransmit).start()

    def receive(self, packet):
        if(self.looseNbReceivePacket > 0):
            self.looseNbReceivePacket -= 1
            print(f"Mock: Node {self.adress} lost packet while receiving")
            return
        if(self.looseReceivePacket):
            print(f"Mock: Node {self.adress} lost packet while receiving")
            return
        def asyncReceive():
            print(f"Mock: Node {self.adress} is receiving packet")
            time.sleep(self.receptionDelay)
            self.receivePackets.append(packet)
            print(f"Mock: Node {self.adress} received packet")
            if (packet.header.status & FLAG_R) > 0:
                ResponseWithAckForDelay(self, packet)
            if self.onReceive is not None:
                self.onReceive(self, packet)

        threading.Thread(target=asyncReceive).start()

