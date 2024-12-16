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
        self.assignedTransmitDelaysUs = {}
        self.modemGateway: IModem = modemGateway
        self.topology: [] = topology
        self.nodeTwoWayTimeOfFlightUs: Dict[str, int] = {}
        self.dataPacketOctetSize = 512
        self.nodeDataPacketTransmitTimeUs = int(5 * 1e6)
        self.guardIntervalUs = int(1 * 1e6)
        self.timeoutPingSec = 5
        self.receivedPaquetOfCurrentReq = {}
        self.receivedPaquets = []
        self.receivePacketTimeUs = {}
        self.ReceiveAllDataPacketEvent = threading.Event()
        self.timeoutDataRequestSec = 20
        self.jitterThresholdUs = 100 * 1000
        self.periodeSec = int(60 * 4)
        self.running = False
        self.dataPaquetSequenceNumber = 0

    @classmethod
    def fromSerialPort(cls, serialport: str, topology: []):
        modem = Modem()
        modem.connect(serialport)
        modem.receive()
        return cls(modem, topology)

    def run(self):
        self.pingTopology()
        self.calculateNodesDelay()
        self.sendAssignedTransmitDelaysToNodes()
        self.main()

    def pingTopology(self):
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
            elpasedTimeSec = time.time() - (transmitTimeUs / 1000)
            time.sleep(max(self.periodeSec - elpasedTimeSec, 0))
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
