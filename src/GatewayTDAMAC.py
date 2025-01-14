from .i_modem import IModem
import threading
from typing import Dict
from lib.ahoi.modem.packet import printPacket
from src.modem import Modem
from src.constantes import BROCAST_ADDRESS, GATEWAY_ID, ID_PAQUET_TDI, ID_PAQUET_REQ_DATA, ID_PAQUET_PING, FLAG_R, \
    ID_PAQUET_DATA
import time


class GatewayTDAMAC:
    """Implementation of the TDMA MAC protocol for the gateway
    The gateway is responsible for the synchronization of the network
    and the transmission of data packets to the nodes.
    """
    def __init__(self, modemGateway: IModem, topology: []):
        """Constructor of the GatewayTDAMAC class

        Args:
            modemGateway (IModem): The modem gateway used to communicate with the nodes
            the modem should be connected and receiving before creating the gateway
            topology ([]): The list of nodes in the network
        """
        # Todo: assert the modem is connected and receiving
        self.assignedTransmitDelaysUs = {}  # Dictionary of assigned transmission delays
        self.modemGateway: IModem = modemGateway  # Modem used to communicate with the nodes
        self.topology: [] = topology  # List of nodes in the network
        self.nodeTwoWayTimeOfFlightUs: Dict[str, int] = {}  # Two-way time of flight of the nodes
        self.dataPacketOctetSize = 512  # Size of data packets in octets
        self.nodeDataPacketTransmitTimeUs = int(0.32768 * 1e6) # TODO: calculer sur la base des paramètre de modulation du modem et de la taille de trame
        self.guardIntervalUs = int(1 * 1e6)  # Guard interval in µs
        self.timeoutPingSec = 5  # Timeout for ping in seconds
        self.receivedPaquetOfCurrentReq = {}  # Packets received for the current request
        self.receivedPaquets = []  # List of received packets
        self.receivePacketTimeUs = {}  # Reception time of packets
        self.ReceiveAllDataPacketEvent = threading.Event()  # Event to signal reception of all data packets
        self.timeoutDataRequestSec = 20  # Timeout for data request in seconds
        self.jitterThresholdUs = 100 * 1e3  # Jitter threshold in µs
        self.periodeSec = int(60 * 4)  # Period in seconds
        self.running = False  # Flag to indicate if the gateway is running
        self.dataPaquetSequenceNumber = 0  # Sequence number for data packets

    @classmethod
    def fromSerialPort(cls, serialport: str, topology: []):
        modem = Modem()
        modem.connect(serialport)
        modem.receive()
        return cls(modem, topology)

    def run(self):
        """
        Runs the main sequence of operations for the GatewayTDAMAC.

        1. Pings the network topology to gather information about the nodes.
        2. Calculates the delay for each node in the network.
        3. Sends the assigned transmission delays to the nodes.
        4. Executes the main function of the GatewayTDAMAC.

        Returns:
            None
        """
        self.pingTopology()
        self.calculateNodesDelay()
        self.sendAssignedTransmitDelaysToNodes()
        self.main()

    def pingTopology(self):
        """
        Pings all nodes in the topology to measure the two-way time of flight.

        This function sends a ping packet to each node in the topology and waits for a response.
        If a response is received within the specified timeout, the two-way time of flight is recorded.
        If no response is received, the ping is retried until a response is received or the maximum number of attempts is reached.

        Attributes:
            event (threading.Event): Event to manage the synchronization of ping responses.
            nodeTwoWayTimeOfFlightUs (dict): Dictionary to store the two-way time of flight for each node.

        Modem Callback:
            modemCallback(pkt): Callback function to handle incoming packets and check for ranging acknowledgments.

        Process:
            - Adds the modem callback to handle incoming packets.
            - Iterates through each node in the topology.
            - Sends a ping packet to the node and waits for a response.
            - If a response is received, records the time of flight and proceeds to the next node.
            - If no response is received, retries the ping until a response is received or the maximum number of attempts is reached.
            - Removes the modem callback after all nodes have been pinged.

        Raises:
            None

        Returns:
            None
        """

        self.event = threading.Event()
        self.nodeTwoWayTimeOfFlightUs = {}

        def modemCallback(pkt):
            # check if we have received a ranging ack
            if pkt.header.type == ID_PAQUET_PING and pkt.header.len > 0:
                self.nodeTwoWayTimeOfFlightUs[pkt.header.src] = int.from_bytes(pkt.payload, 'big')
                self.event.set()  # liberate the event to get the next node time of flight

        self.modemGateway.addRxCallback(modemCallback)

        for node in self.topology:
            nb_attempts = 0
            while True:
                print("Gateway: Pinging node " + str(node))
                self.modemGateway.send(src=GATEWAY_ID, dst=node, type=ID_PAQUET_PING, payload=bytearray(), status=FLAG_R, dsn=0)
                if self.event.wait(timeout=self.timeoutPingSec):
                    self.event.clear()
                    print(f"Succès de la réponse du nœud {node}")
                    break
                else:
                    nb_attempts += 1
                    print(f"Tentative nb: " + str(nb_attempts) + "Aucune réponse du nœud {node}. Renvoi du paquet ")

        self.modemGateway.removeRxCallback(modemCallback)

    def calculateNodesDelay(self):
        """
        Calculate the transmission delay for each node in the topology.

        This method initializes the transmission delay for the first node to 0.
        For each subsequent node, it calculates the transmission delay based on
        the previous node's delay, the node's two-way time of flight, the data
        packet transmission time, and the guard interval.

        The calculated delays are stored in the `assignedTransmitDelaysUs` dictionary,
        where the keys are the nodes and the values are their respective transmission delays.

        Raises:
            KeyError: If `self.topology` or `self.nodeTwoWayTimeOfFlightUs` does not contain
                  the necessary nodes.
        """

        self.assignedTransmitDelaysUs = {}
        # transmit delay of the first node is 0
        self.assignedTransmitDelaysUs[self.topology[0]] = 0

        for i in range(1, len(self.topology)):
            assignedTransmitDelayPrevious = self.assignedTransmitDelaysUs[self.topology[i - 1]]
            transmitDelayToNode = self.nodeTwoWayTimeOfFlightUs[self.topology[i]] // 2
            transmitDelayToPreviousNode = self.nodeTwoWayTimeOfFlightUs[self.topology[i - 1]] // 2

            self.assignedTransmitDelaysUs[self.topology[i]] = \
                assignedTransmitDelayPrevious + \
                self.nodeDataPacketTransmitTimeUs + \
                self.guardIntervalUs + \
                - 2 * (transmitDelayToNode - transmitDelayToPreviousNode)

    def sendAssignedTransmitDelaysToNodes(self):
        """
        Send assigned transmit delays to all nodes in the topology.

        This method iterates over each node in the topology and sends a message
        containing the assigned transmit delay to each node using the modem gateway.
        """
        for node in self.topology:
            self.modemGateway.send(
                src=GATEWAY_ID,
                dst=node,
                type=ID_PAQUET_TDI,
                payload=self.assignedTransmitDelaysUs[node].to_bytes(4, 'big'),
                status=0,
                dsn=0
            )

    def main(self):
        """
        Main function to manage the gateway's data packet reception and transmission.

        This function sets up the modem gateway to receive data packets, waits for all data packets to be received,
        handles timeouts, checks for jitter, and retransmits delays if necessary. It runs in a loop until the
        `self.running` flag is set to False.
        """

        self.modemGateway.addRxCallback(self.packetCallback)
        self.running = True
        while self.running:
            self.receivedPaquetOfCurrentReq = {}
            self.receivePacketTimeUs = {}
            self.ReceiveAllDataPacketEvent.clear()
            transmitTimeUs = time.time() * 1e6 # to convert to µs
            self.RequestDataPacket()
            print("Gateway: Waiting for all data packets...")
            if self.ReceiveAllDataPacketEvent.wait(timeout=self.timeoutDataRequestSec):
                print("All data packets received")
                # TODO: handle data packets
            else:
                print("Timeout on data packets reception")
                # TODO: handle timeout

            mustRestransmitDelays = False
            for nodeId in self.topology:
                if nodeId not in self.receivedPaquetOfCurrentReq:
                    # TODO:  if it's the first time we don't receive the data packet of node x
                    # retranmist the tdi packet to node x
                    # else
                    # do nothing
                    # or determine if we should increase the guard interval or timeout
                    continue

                # check if the packet arrived at the expected time
                expectedArrivalTime = transmitTimeUs + \
                                      self.nodeTwoWayTimeOfFlightUs[nodeId] + \
                                      self.assignedTransmitDelaysUs[nodeId]
                actualArrivalTime = self.receivePacketTimeUs[nodeId]
                # TODO: Correct the diff calculation
                diff = abs(actualArrivalTime - expectedArrivalTime)
                if diff > self.jitterThresholdUs:
                    print(f"Node {nodeId} gigue/jitter: {diff}")
                    # TODO: Adjust transmit delays
                    mustRestransmitDelays = True

            if mustRestransmitDelays:
                self.modemGateway.removeRxCallback(self.packetCallback)
                self.calculateNodesDelay()
                self.sendAssignedTransmitDelaysToNodes()
                self.modemGateway.addRxCallback(self.packetCallback)

            if not self.running:
                break
            # wait for the next period
            #elpasedTimeSec = time.time() - (transmitTimeUs / 1000)
            time.sleep(self.periodeSec)
        self.modemGateway.removeRxCallback(self.packetCallback)

    def packetCallback(self, pkt):
        # check if we have received a data packet
        if pkt.header.type == ID_PAQUET_DATA and pkt.header.dsn == self.dataPaquetSequenceNumber:
            self.receivedPaquetOfCurrentReq[pkt.header.src] = pkt
            self.receivePacketTimeUs[pkt.header.src] = time.time() * 1e6 # to convert to µs
            self.receivedPaquets.append(pkt)

            # check if we have received all data packets of the topology
            if len(self.receivedPaquetOfCurrentReq) == len(self.topology):
                self.ReceiveAllDataPacketEvent.set()
        elif pkt.header.type == ID_PAQUET_DATA:
            print("Received packet with wrong data sequence number")
        else:
            print("Received packet with unknown type")
            printPacket(pkt)
        pass

    def RequestDataPacket(self):
        self.dataPaquetSequenceNumber = (self.dataPaquetSequenceNumber + 1) % 256
        self.modemGateway.send(
            src=GATEWAY_ID,
            dst=BROCAST_ADDRESS,
            type=ID_PAQUET_REQ_DATA,
            payload=bytearray(),
            status=0,
            dsn=self.dataPaquetSequenceNumber
        )
