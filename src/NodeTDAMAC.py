import time
from enum import Enum, auto
from src.i_modem import IModem
import threading
from src.constantes import ID_PAQUET_TDI, GATEWAY_ID, ID_PAQUET_DATA, ID_PAQUET_REQ_DATA
from queue import Queue
import threading


class NodeTDAMAC:
    def __init__(self, modem: IModem, address: int):
        self.address = address
        self.tdiPacketEvent = None
        self.modem: IModem = modem
        self.running = False
        self.assignedTransmitDelaysUs: int = -1
        self.messageToSendQueue: Queue[bytearray] = Queue()
        self.modem.addRxCallback(self.NodeCallBack)

    def waitForTDIPacket(self):
        if self.assignedTransmitDelaysUs >= 0:
            return
        self.tdiPacketEvent = threading.Event()
        self.tdiPacketEvent.wait()
        self.tdiPacketEvent = None

    def NodeCallBack(self, packet):
        if packet.header.type == ID_PAQUET_TDI:
            self.assignedTransmitDelaysUs = int.from_bytes(packet.payload, 'big')
            if self.tdiPacketEvent is not None:
                self.tdiPacketEvent.set()
        if packet.header.type == ID_PAQUET_REQ_DATA:
            print("node: Received request for data")
            if self.messageToSendQueue.empty():
                return
            print("node: Sending data..")
            data = self.messageToSendQueue.get()

            def sendAsync():
                time.sleep(self.assignedTransmitDelaysUs * 1e-6)
                self.modem.send(
                    src=self.address,
                    dst=GATEWAY_ID,
                    type=ID_PAQUET_DATA,
                    payload=data,
                    status=0,
                    dsn=packet.header.dsn
                )
            threading.Thread(target=sendAsync).start()

    def send(self, data: bytearray):
        if self.assignedTransmitDelaysUs < 0:
            self.waitForTDIPacket()
        self.messageToSendQueue.put(data)
