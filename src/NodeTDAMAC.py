import time
from enum import Enum, auto
from src.i_modem import IModem
import threading
from src.constantes import ID_PAQUET_TDI, ID_PAQUET_DATA, ID_PAQUET_REQ_DATA
from src.modem import Modem
from queue import Queue
import threading


class NodeTDAMAC:
    """Implementation of the TDMA MAC protocol for the nodes
    The nodes are responsible for the transmission of data packets to the gateway
    and the reception of packets from the gateway.
    """

    def __init__(self, modem: IModem, address: int, gatewayAddress: int = 0):
        """Constructor of the NodeTDAMAC class

        Args:
            modem (IModem): The modem used to communicate with the gateway
            the modem should be connected and receiving before creating the node
            address (int): The address of the node
        """
        # Todo: assert the modem is connected and receiving
        # Initialize the node address
        self.address = address  # Node address
        self.tdiPacketEvent = None  # Event to wait for the TDI packet
        self.modem: IModem = modem  # Modem instance for communication
        self.running = False  # Flag to indicate if the node is running
        self.assignedTransmitDelaysUs: int = -1  # Assigned transmit delay in microseconds, -1 indicates not assigned
        self.messageToSendQueue: Queue[bytearray] = Queue()  # Queue to hold messages to be sent
        self.gatewayId = gatewayAddress

        # Register the callback function for received packets
        self.modem.addRxCallback(self.NodeCallBack)

    @classmethod
    def fromSerialPort(cls, serialport: str, topology: []):
        # Create a modem instance and connect it to the serial port
        modem = Modem()
        modem.connect(serialport)
        modem.receive()
        # Return an instance of NodeTDAMAC
        return cls(modem, topology)

    def waitForTDIPacket(self):
        # Wait for the TDI packet if the transmit delay is not assigned
        if self.assignedTransmitDelaysUs >= 0:
            return
        self.tdiPacketEvent = threading.Event()
        self.tdiPacketEvent.wait()
        self.tdiPacketEvent = None

    def NodeCallBack(self, packet):
        # Handle the received packet based on its type
        if packet.header.type == ID_PAQUET_TDI:
            print("node: Received TDI packet")
            
            # Assign the transmit delay from the packet payload
            self.assignedTransmitDelaysUs = int.from_bytes(packet.payload, 'big')
            if self.tdiPacketEvent is not None:
                self.tdiPacketEvent.set()
        if packet.header.type == ID_PAQUET_REQ_DATA:
            print("node: Received request for data")
            if self.messageToSendQueue.empty():
                data = bytearray("Empty queue", 'utf-8')
            else :
                data = self.messageToSendQueue.get()

            print("node: Sending data..")

            def sendAsync():
                # Wait for the assigned transmit delay before sending data
                time.sleep(self.assignedTransmitDelaysUs * 1e-6)
                self.modem.send(
                    src=self.address,
                    dst=self.gatewayId,
                    type=ID_PAQUET_DATA,
                    payload=data,
                    status=0,
                    dsn=packet.header.dsn
                )
            # Send data asynchronously
            threading.Thread(target=sendAsync).start()

    def send(self, data: bytearray):
        # Wait for the TDI packet if the transmit delay is not assigned
        if self.assignedTransmitDelaysUs < 0:
            self.waitForTDIPacket()
        # Add the data to the send queue
        self.messageToSendQueue.put(data)
