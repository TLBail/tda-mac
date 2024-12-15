import time
from enum import Enum, auto
from src.i_modem import IModem
import threading
from src.constantes import ID_PAQUET_TDI, GATEWAY_ID, ID_PAQUET_DATA, ID_PAQUET_REQ_DATA
from queue import Queue
import threading


class NodeTDAMAC:
    def __init__(self, modem: IModem):
        self.tdiPacketEvent = None
        self.modem: IModem = modem
        self.running = False
        self.assignedTransmitDelaysMs: int = -1
        self.messageToSendQueue: Queue[bytearray] = Queue()
        self.modem.addRxCallback(self.NodeCallBack)

    def waitForTDIPacket(self):
        if self.assignedTransmitDelaysMs >= 0:
            return
        self.tdiPacketEvent = threading.Event()
        self.tdiPacketEvent.wait()
        self.tdiPacketEvent = None

    def NodeCallBack(self, packet):
        if packet.header.type == ID_PAQUET_TDI:
            self.assignedTransmitDelaysMs = int.from_bytes(packet.payload, 'big')
            if self.tdiPacketEvent is not None:
                self.tdiPacketEvent.set()
        if packet.header.type == ID_PAQUET_REQ_DATA:
            print("node: Received request for data")
            if self.messageToSendQueue.empty():
                return
            print("node: Sending data..")
            data = self.messageToSendQueue.get()

            def sendAsync():
                time.sleep(self.assignedTransmitDelaysMs * 1e-6)
                self.modem.send(
                    dst=GATEWAY_ID,
                    src=1,
                    type=ID_PAQUET_DATA,
                    payload=data,
                    status=0,
                    dsn=packet.header.dsn
                )
            threading.Thread(target=sendAsync).start()

    def send(self, data: bytearray):
        if self.assignedTransmitDelaysMs < 0:
            self.waitForTDIPacket()
        self.messageToSendQueue.put(data)
