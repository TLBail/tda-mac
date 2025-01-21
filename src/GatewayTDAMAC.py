from .i_modem import IModem
import threading
from typing import Dict
from lib.ahoi.modem.packet import printPacket
from src.modem import Modem
from src.constantes import BROCAST_ADDRESS, GATEWAY_ID, ID_PAQUET_TDI, ID_PAQUET_REQ_DATA, ID_PAQUET_PING, FLAG_R, \
    ID_PAQUET_DATA
from src.ModemTransmissionCalculator import ModemTransmissionCalculator
import time

from src.utils.Logger import Logger as L

Logger = L("GATEWAY")


class GatewayTDAMAC:
    """Implementation of the TDMA MAC protocol for the gateway
    The gateway is responsible for the synchronization of the network
    and the transmission of data packets to the nodes.
    """
    def __init__(self, modemGateway: IModem,
                 topology: [],
                 dataPacketOctetSize: int = 8,
                 transmitTimeCalc: ModemTransmissionCalculator = ModemTransmissionCalculator(),
                 nbReqMax: int = -1,
                 maxAttemps : int = 10
                 ):
        """Constructor of the GatewayTDAMAC class

        Args:
            modemGateway (IModem): The modem gateway used to communicate with the nodes
            transmitTimeCalc (ModemTransmissionCalculator): The modem transmission calculator
            the modem should be connected and receiving before creating the gateway
            topology ([]): The list of nodes in the network
        """
        self.assignedTransmitDelaysUs = {}  # Dictionary of assigned transmission delays
        self.modemGateway: IModem = modemGateway  # Modem used to communicate with the nodes
        self.topology: [] = topology  # List of nodes in the network
        self.nodeTwoWayTimeOfFlightUs: Dict[str, int] = {}  # Two-way time of flight of the nodes
        self.dataPacketOctetSize = dataPacketOctetSize  # Size of data packets in octets
        self.transmitTimeCalc = transmitTimeCalc  # Modem transmission calculator
        self.nodeDataPacketTransmitTimeUs = transmitTimeCalc.calculate_transmission_time(self.dataPacketOctetSize * 8)
        self.guardIntervalUs = int(2 * 1e6)  # Guard interval in µs
        self.timeoutPingSec = 5  # Timeout for ping in seconds
        self.receivedPaquetOfCurrentReq = {}  # Packets received for the current request
        self.nbReqMax = nbReqMax  # Maximum number of requests
        self.receivedPaquets = []  # List of received packets
        self.receivePacketTimeUs = {}  # Reception time of packets
        self.ReceiveAllDataPacketEvent = threading.Event()  # Event to signal reception of all data packets
        self.timeoutDataRequestSec = 5  # Timeout for data request in seconds in addition to the last node delay
        self.jitterThresholdUs = 100 * 1e3  # Jitter threshold in µs
        self.periodeSec = int(20)  # Period in seconds
        self.running = False  # Flag to indicate if the gateway is running
        self.dataPaquetSequenceNumber = 0  # Sequence number for data packets
        self.gatewayId = GATEWAY_ID  # Gateway address
        self.maxAttemps = maxAttemps  # Maximum number of attempts for ping until the node is considered unreachable (not included)

        # temporary variables
        self.receivedTime = -1
        self.expectedNodeAdress = -1

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
        if len(self.topology) == 0:
            raise ValueError("Topology is empty")
        self.pingTopology()
        if len(self.topology) == 0:
            raise ValueError("Topology is empty")
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
        """
        self.event = threading.Event()
        self.nodeTwoWayTimeOfFlightUs = {}

        self.expectedNodeAdress = self.topology[0]
        self.receivedTime = -1

        def modemCallback(pkt):
            # check if we have received a ranging ack
            if pkt.header.type == ID_PAQUET_PING and pkt.header.len > 0 \
                    and pkt.header.src == self.expectedNodeAdress:
                self.receivedTime = time.time_ns()
                tof = 0
                # Calcul the ToF value
                for i in range(0, 4):
                    tof = tof * 256 + pkt.payload[i]

                self.nodeTwoWayTimeOfFlightUs[pkt.header.src] = tof
                self.event.set()  # liberate the event to get the next node time of flight

        self.modemGateway.addRxCallback(modemCallback)

        for node in self.topology:
            nb_attempts = 0
            self.expectedNodeAdress = node
            while True:
                # print("Gateway: Pinging node " + str(node))

                Logger.info(f"Pinging node {node}")
                self.receivedTime = -1
                pingSendTimeNs = time.time_ns()
                self.modemGateway.send(src=self.gatewayId, dst=node, type=ID_PAQUET_PING, payload=bytearray(), status=FLAG_R, dsn=0)
                if self.event.wait(timeout=self.timeoutPingSec):
                    self.event.clear()
                    # print(f"Succès de la réponse du nœud {node}")
                    if self.receivedTime == -1:
                        raise Exception("Received time is not set")
                    timeOfFlightEndToEnd = self.receivedTime - pingSendTimeNs
                    Logger.info(f"Node {node} answered successfully in {self.nodeTwoWayTimeOfFlightUs[node] * 1e-3} ms and E2E {timeOfFlightEndToEnd * 1e-6} ms")
                    break
                else:
                    nb_attempts += 1
                    # print(f"Tentative nb: " + str(nb_attempts) + "Aucune réponse du nœud {node}. Renvoi du paquet ")
                    if nb_attempts >= self.maxAttemps:
                        Logger.error(f"No response from node {node}. "
                                     f"Maximum number of attempts reached. "
                                     f"Removing node from topology")
                        self.topology.remove(node)
                        break
                    else:
                        Logger.warning(f"Attempt nb: {nb_attempts} No response from node {node}. Resending the packet")

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
        self.topology.sort(key=lambda x: self.nodeTwoWayTimeOfFlightUs[x])
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
                src=self.gatewayId,
                dst=node,
                type=ID_PAQUET_TDI,
                payload=self.assignedTransmitDelaysUs[node].to_bytes(4, 'big'),
                status=0,
                dsn=0
            )

            # print(f"Gateway : sending delay to {node} - Assigned {self.assignedTransmitDelaysUs[node]}µs")
            Logger.info(f"Gateway : sending delay to {node} - Assigned {self.assignedTransmitDelaysUs[node]}µs")

    def main(self):
        """
        Main function to manage the gateway's data packet reception and transmission.

        This function sets up the modem gateway to receive data packets, waits for all data packets to be received,
        handles timeouts, checks for jitter, and retransmits delays if necessary. It runs in a loop until the
        `self.running` flag is set to False.
        """

        self.modemGateway.addRxCallback(self.packetCallback)
        self.running = True
        nbReq = 0
        while self.running:
            if self.nbReqMax != -1 and nbReq >= self.nbReqMax:
                break
            nbReq += 1
            self.receivedPaquetOfCurrentReq = {}
            self.receivePacketTimeUs = {}
            self.ReceiveAllDataPacketEvent.clear()
            transmitTimeUs = time.time_ns() * 1e-3 # to convert to µs
            self.RequestDataPacket()
            # print("Gateway: Waiting for all data packets...")
            # print("Gateway: Waiting for " + str(len(self.topology)) + " nodes")
            # print("Gateway: Timeout set to " + str(self.getTimeoutDataRequestSec()) + " seconds")

            Logger.debug("Gateway: Waiting for all data packets...")
            Logger.debug(f"Gateway: Waiting for {len(self.topology)} nodes")
            Logger.debug(f"Gateway: Timeout set to {self.getTimeoutDataRequestSec()} seconds")
            if self.ReceiveAllDataPacketEvent.wait(timeout=self.getTimeoutDataRequestSec()):
                # print("All data packets received")
                Logger.debug("All data packets received")
                # TODO: handle data packets
            else:
                # print("Timeout on data packets reception")
                Logger.error("Timeout on data packets reception")
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
                diff = abs(actualArrivalTime - expectedArrivalTime)
                if diff > self.jitterThresholdUs:
                    # print(f"Node {nodeId} gigue/jitter: {diff}")
                    Logger.warning(f"Node {nodeId} gigue/jitter: {diff}")
                    # TODO: Adjust transmit delays
                    #mustRestransmitDelays = True

            if mustRestransmitDelays:
                self.modemGateway.removeRxCallback(self.packetCallback)
                self.calculateNodesDelay()
                self.sendAssignedTransmitDelaysToNodes()
                self.modemGateway.addRxCallback(self.packetCallback)

            if not self.running:
                break
            # wait for the next period
            elpasedTimeSec = time.time() - (transmitTimeUs * 1e-6)
            waitTimeSec = max(0, self.periodeSec - elpasedTimeSec)
            # print(f"Gateway: Waiting for {waitTimeSec} seconds before the next period")
            Logger.debug(f"Gateway: Waiting for {waitTimeSec} seconds before the next period")
            time.sleep(waitTimeSec)
        self.modemGateway.removeRxCallback(self.packetCallback)
        print("Gateway: nb data packet received" + str(len(self.receivedPaquets)))
        for i in range(len(self.topology)):
            # filter the received packets by node
            nbPacket = 0
            for pkt in self.receivedPaquets:
                if pkt.header.src == self.topology[i]:
                    nbPacket += 1
            print(f"Node {self.topology[i]} received {nbPacket} packets")

    def packetCallback(self, pkt):
        if pkt.header.src == self.gatewayId:
            return
        printPacket(pkt)
        # check if we have received a data packet
        if pkt.header.type == ID_PAQUET_DATA and pkt.header.dsn == self.dataPaquetSequenceNumber:
            self.receivedPaquetOfCurrentReq[pkt.header.src] = pkt
            self.receivePacketTimeUs[pkt.header.src] = time.time() * 1e6 # to convert to µs
            self.receivedPaquets.append(pkt)

            # check if we have received all data packets of the topology
            if len(self.receivedPaquetOfCurrentReq) == len(self.topology):
                self.ReceiveAllDataPacketEvent.set()
        elif pkt.header.type == ID_PAQUET_DATA:
            # print("Received packet with wrong data sequence number")
            Logger.error("Received packet with wrong data sequence number")
        else:
            # print("Received packet with unknown type")
            Logger.warning("Received packet with unknown type")
            printPacket(pkt)
        pass

    def RequestDataPacket(self):
        self.dataPaquetSequenceNumber = (self.dataPaquetSequenceNumber + 1) % 256
        self.modemGateway.send(
            src=self.gatewayId,
            dst=BROCAST_ADDRESS,
            type=ID_PAQUET_REQ_DATA,
            payload=bytearray(),
            status=0,
            dsn=self.dataPaquetSequenceNumber
        )

    def setDataPaquetSize(self, size: int):
        self.dataPacketOctetSize = size
        self.nodeDataPacketTransmitTimeUs = self.transmitTimeCalc.calculate_transmission_time(self.dataPacketOctetSize * 8)

    def getTimeoutDataRequestSec(self):
        return self.timeoutDataRequestSec + \
            (self.assignedTransmitDelaysUs[self.topology[-1]] * 1e-6) + \
            (self.guardIntervalUs * 1e-6)
