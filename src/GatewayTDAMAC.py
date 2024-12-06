from .i_modem import IModem
import threading
from typing import Dict
from lib.ahoi.modem.packet import printPacket
import time


class NodeInfo:
    def __init__(self, receptionDelayMs: int, transmitDelayMs: int):
        self.receptionDelayMs = receptionDelayMs
        self.transmitDelayMs = transmitDelayMs


class GatewayTDAMAC:
    def __init__(self, modemGateway: IModem, topology: []):
        self.assignedTransmitDelaysMs = {}
        self.modemGateway: IModem = modemGateway
        self.topology: [] = topology
        self.nodesInfo: Dict[str, NodeInfo] = {}
        self.dataPacketOctetSize = 512
        self.nodeDataPacketTransmitTimeMs = 5 * 1e6
        self.guardIntervalMs = 1 * 1e6
        self.timeoutPingSec = 5
        self.pingPacketTypeId = 0x7F
        self.tdipacketTypeId = 1
        self.gatewayId = 0
        self.broadcastAddress = 255
        self.receivePacket = {}
        self.receivePacketTimeMs = {}
        self.DataRequestEvent = threading.Event()
        self.timeoutDataRequestSec = 20
        self.jitterThresholdMs = 1000

    def run(self):
        self.pingTopology()
        self.calculateNodesDelay()
        self.sendAssignedTransmitDelaysToNodes()
        self.main()

    def pingTopology(self):
        self.event = threading.Event()
        self.nodesInfo = {}

        def modemCallback(pkt):
            # check if we have received a ranging ack
            if pkt.header.type == self.pingPacketTypeId and pkt.header.len > 0:
                # calculate time of flight
                received_receptionDelay = int.from_bytes(pkt.payload[:4], 'big')
                received_transmitDelay = int.from_bytes(pkt.payload[4:], 'big')
                self.nodesInfo[pkt.header.src] = NodeInfo(
                    received_receptionDelay,
                    received_transmitDelay
                )
                self.event.set()  # liberate the event to get the next node time of flight

        self.modemGateway.addRxCallback(modemCallback)

        for node in self.topology:

            nb_attempts = 0
            while True:
                self.modemGateway.send(node, self.gatewayId, self.pingPacketTypeId, int(0).to_bytes(4, 'big'), 0)
                if self.event.wait(timeout=self.timeoutPingSec):
                    self.event.clear()
                    print(f"Succès de la réponse du nœud {node}")
                    break
                else:
                    nb_attempts += 1
                    print(f"Tentative nb: " + str(nb_attempts) + "Aucune réponse du nœud {node}. Renvoi du paquet ")


        self.modemGateway.removeRxCallback(modemCallback)

    def calculateNodesDelay(self):
        self.assignedTransmitDelaysMs = {}
        # transmit of the first node is 0
        self.assignedTransmitDelaysMs[self.topology[0]] = 0

        for i in range(1, len(self.topology)):
            assignedTransmitDelayPrevious = self.assignedTransmitDelaysMs[self.topology[i - 1]]
            transmitDelayToNode = self.nodesInfo[self.topology[i]].transmitDelayMs
            transmitDelayToPreviousNode = self.nodesInfo[self.topology[i - 1]].transmitDelayMs

            self.assignedTransmitDelaysMs[self.topology[i]] = \
                assignedTransmitDelayPrevious + \
                self.nodeDataPacketTransmitTimeMs + \
                self.guardIntervalMs + \
                - 2 * (transmitDelayToNode - transmitDelayToPreviousNode)

    def sendAssignedTransmitDelaysToNodes(self):
        for node in self.topology:
            self.modemGateway.send(
                node,
                self.gatewayId,
                self.tdipacketTypeId,
                self.assignedTransmitDelaysMs[node].to_bytes(4, 'big'),
                0
            )


    def main(self):
        self.modemGateway.addRxCallback(self.packetCallback)
        while True:
            self.receivePacket = {}
            self.receivePacketTimeMs = {}
            self.DataRequestEvent.clear()
            transmitTimeMs = time.time() * 1000
            self.RequestDataPacket()
            if self.DataRequestEvent.wait(timeout=self.timeoutDataRequestSec):
                print("All data packets received")
                # TODO: handle data packets
            else:
                print("Timeout on data packets reception")
                # TODO: handle timeout
            for nodeId in self.topology:
                expectedArrivalTime = transmitTimeMs + \
                                      self.nodesInfo[nodeId].receptionDelayMs + \
                                      self.assignedTransmitDelaysMs[nodeId] + \
                                      self.nodesInfo[nodeId].transmitDelayMs
                actualArrivalTime = self.receivePacketTimeMs[nodeId]
                diff = abs(actualArrivalTime - expectedArrivalTime)
                print(f"Node {nodeId} error: {diff}")
                if diff > self.jitterThresholdMs:
                    # TODO: Adjust transmit delays
                    self.modemGateway.removeRxCallback(self.packetCallback)
                    self.calculateNodesDelay()
                    self.sendAssignedTransmitDelaysToNodes()
                    self.modemGateway.addRxCallback(self.packetCallback)
        self.modemGateway.removeRxCallback(self.packetCallback)

    def packetCallback(self, pkt):
        # check if we have received a data packet
        if pkt.header.type == self.pingPacketTypeId and pkt.header.len > 0:
            self.receivePacket[pkt.header.src] = pkt
            self.receivePacketTimeMs[pkt.header.src] = time.time() * 1000

            # check if we have received all data packets of the topology
            if len(self.receivePacket) == len(self.topology):
                self.DataRequestEvent.set()
        else:
            print("Received packet with unknown type")
            printPacket(pkt)
        pass

    def RequestDataPacket(self):
        self.modemGateway.send(
            self.broadcastAddress,
            self.gatewayId,
            self.tdipacketTypeId,
            int(0).to_bytes(4, 'big'),
            0
        )
