import time
from src.i_modem import IModem
import threading
from src.constantes import ID_PAQUET_TDI, ID_PAQUET_DATA, ID_PAQUET_REQ_DATA, PAQUET_SIZE
from src.modem import Modem
from src.ModemTransmissionCalculator import ModemTransmissionCalculator
from lib.ahoi.modem.packet import makePacket, printPacket
import threading
from typing import List
from src.utils.Logger import Logger as L

Logger = L("NODE")


class NodeTDAMAC:
    """Implementation of the TDMA MAC protocol for the nodes
    The nodes are responsible for the transmission of data packets to the gateway
    and the reception of packets from the gateway.
    """

    def __init__(self, modem: IModem,
                 address: int,
                 gatewayAddress: int = 0,
                 dataPacketOctetSize: int = PAQUET_SIZE,
                 transmitTimeCalc: ModemTransmissionCalculator = ModemTransmissionCalculator(),
                 responsePayload: bytearray = bytearray("no payload", 'utf-8')
                 ):
        """Constructor of the NodeTDAMAC class

        Args:
            modem (IModem): The modem used to communicate with the gateway
            transmitTimeCalc (ModemTransmissionCalculator): The modem transmission calculator
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
        self.gatewayId = gatewayAddress
        self.dataPacketOctetSize = dataPacketOctetSize
        self.transmitTimeCalc = transmitTimeCalc
        self.nodeDataPacketTransmitTimeUs = transmitTimeCalc.calculate_transmission_time(self.dataPacketOctetSize * 8)
        self.responsePayload = responsePayload

        # Register the callback function for received packets
        self.modem.addRxCallback(self.NodeCallBack)

    @classmethod
    def fromSerialPort(cls, serialport: str, topology: List):
        # Create a modem instance and connect it to the serial port
        modem = Modem()
        modem.connect(serialport)
        modem.receive()

        # Return an instance of NodeTDAMAC
        address = topology[0] if topology else 0
        return cls(modem, address)

    def setReponsePayload(self, payload: bytearray):
        self.responsePayload = payload

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
            # print("node: Received TDI packet")
            Logger.debug(f"Received TDI packet")
            
            # Assign the transmit delay from the packet payload
            self.assignedTransmitDelaysUs = int.from_bytes(packet.payload, 'big')
            Logger.info(f"Transmit delay is assigned to {self.assignedTransmitDelaysUs}µs")
            if self.tdiPacketEvent is not None:
                self.tdiPacketEvent.set()

        if packet.header.type == ID_PAQUET_REQ_DATA:
            # print("node: Received request for data")
            Logger.debug(f"Received request for data")
            
            if (self.assignedTransmitDelaysUs is None): 
                # print("node: Transmit delay is not assigned")
                Logger.info(f"Transmit delay is not assigned")
                return

            # print("node: Sending data..")
            Logger.info(f"Sending data..")

            def sendAsync():
                # Wait for the assigned transmit delay before sending data
                time.sleep(max(self.assignedTransmitDelaysUs * 1e-6, 0))
                pkt = makePacket(
                    src=self.address,
                    dst=self.gatewayId,
                    type=ID_PAQUET_DATA,
                    payload=self.responsePayload,
                    dsn=packet.header.dsn
                )
                printPacket(pkt)
                Logger.debug(f"Sent packet [{ID_PAQUET_DATA}] to {self.address}", pkt)
                Logger.logTX(pkt, f"node{self.address}")
                


                self.modem.send(
                    src=self.address,
                    dst=self.gatewayId,
                    type=ID_PAQUET_DATA,
                    payload=self.responsePayload,
                    status=0,
                    dsn=packet.header.dsn
                )
            # Send data asynchronously
            threading.Thread(target=sendAsync).start()