from src.modem_mock import ModemMock
import time
import threading


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

