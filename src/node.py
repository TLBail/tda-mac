from src.modem_mock import ModemMock
import time
import threading
from lib.ahoi.modem.packet import makePacket

def ResponseWithAckForDelay(node, delay):
    """payload is the full time of flight because ModemMock does not simulate time of flight"""
    half_tof = int((node.receptionDelay + node.transmitDelay) * 1e6)  # Convertir en microsecondes
    tof_payload = half_tof.to_bytes(4, 'big')
    ack_packet = makePacket(
        src=node.adress,  # Source devient la destination (ACK retourne au sender)
        dst=0,
        type=0x7F,  # Type pour les ACK de ranging
        payload=tof_payload
    )
    node.transmit(ack_packet)

class Node:

    def __init__(self, modem: ModemMock, adress, onReceive=None):
        self.modem = modem
        self.adress = adress
        self.onReceive = onReceive
        self.receivePackets = []
        self.transmitDelay = 0
        self.receptionDelay = 0

    def transmit(self, packet):
        def asyncTransmit():
            print(f"Node {self.adress} is transmitting packet")
            time.sleep(self.transmitDelay)
            self.modem.simulateRx(packet)
            print(f"Node {self.adress} transmitted packet")

        threading.Thread(target=asyncTransmit).start()

    def receive(self, packet):
        def asyncReceive():
            print(f"Node {self.adress} is receiving packet")
            time.sleep(self.receptionDelay)
            self.receivePackets.append(packet)
            print(f"Node {self.adress} received packet")
            if self.onReceive is not None:
                self.onReceive(self, packet)

        threading.Thread(target=asyncReceive).start()

