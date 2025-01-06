import time
from enum import Enum, auto
from src.i_modem import IModem
import threading
from src.constantes import ID_PAQUET_TDI, GATEWAY_ID, ID_PAQUET_DATA, ID_PAQUET_REQ_DATA
from src.modem import Modem
from queue import Queue
import threading


class NodeTDAMAC:
    """Implementation of the TDMA MAC protocol for the nodes
    The nodes are responsible for the transmission of data packets to the gateway
    and the reception of packets from the gateway.
    """

    def __init__(self, modem: IModem, address: int):
        """Constructor of the NodeTDAMAC class

        Args:
            modem (IModem): The modem used to communicate with the gateway
            the modem should be connected and receiving before creating the node
            address (int): The address of the node
        """
        # Todo: assert the modem is connected and receiving
        self.address = address
        self.tdiPacketEvent = None
        self.modem: IModem = modem
        self.running = False
        self.assignedTransmitDelaysUs: int = -1
        self.messageToSendQueue: Queue[bytearray] = Queue()
        self.modem.addRxCallback(self.NodeCallBack)

    @classmethod
    def fromSerialPort(cls, serialport: str, topology: []):
        modem = Modem()
        modem.connect(serialport)
        modem.receive()
        return cls(modem, topology)

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
