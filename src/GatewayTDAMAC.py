from .i_modem import IModem
import threading
from typing import Dict
from lib.ahoi.modem.packet import printPacket
from src.constantes import BROCAST_ADDRESS, GATEWAY_ID, ID_PAQUET_TDI, ID_PAQUET_REQ_DATA, ID_PAQUET_PING, FLAG_R, \
    ID_PAQUET_DATA
import time


class GatewayTDAMAC:
    def __init__(self, modemGateway: IModem, topology: []):
        self.assignedTransmitDelaysMs = {}
        self.modemGateway: IModem = modemGateway
        self.topology: [] = topology
        self.nodeTwoWayTimeOfFlightMs: Dict[str, int] = {}
        self.dataPacketOctetSize = 512
        self.nodeDataPacketTransmitTimeMs = 5 * 1e6
        self.guardIntervalMs = 1 * 1e6
        self.timeoutPingSec = 5
        self.receivePacket = {}
        self.receivePacketTimeMs = {}
        self.ReceiveAllDataPacketEvent = threading.Event()
        self.timeoutDataRequestSec = 20
        self.jitterThresholdMs = 1000
        self.periodeSec = 60 * 4
        self.running = False

    def run(self):
        self.pingTopology()
        self.calculateNodesDelay()
        self.sendAssignedTransmitDelaysToNodes()
        self.main()

    def pingTopology(self):
        self.event = threading.Event()
        self.nodeTwoWayTimeOfFlightMs = {}

        def modemCallback(pkt):
            # check if we have received a ranging ack
            if pkt.header.type == ID_PAQUET_PING and pkt.header.len > 0:
                self.nodeTwoWayTimeOfFlightMs[pkt.header.src] = int.from_bytes(pkt.payload, 'big')
                self.event.set()  # liberate the event to get the next node time of flight

        self.modemGateway.addRxCallback(modemCallback)

        for node in self.topology:
            nb_attempts = 0
            while True:
                self.modemGateway.send(node, GATEWAY_ID, ID_PAQUET_PING, bytearray(), FLAG_R, 0)
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
        # transmit delay of the first node is 0
        self.assignedTransmitDelaysMs[self.topology[0]] = 0

        for i in range(1, len(self.topology)):
            assignedTransmitDelayPrevious = self.assignedTransmitDelaysMs[self.topology[i - 1]]
            transmitDelayToNode = self.nodeTwoWayTimeOfFlightMs[self.topology[i]] / 2
            transmitDelayToPreviousNode = self.nodeTwoWayTimeOfFlightMs[self.topology[i - 1]] / 2

            self.assignedTransmitDelaysMs[self.topology[i]] = \
                assignedTransmitDelayPrevious + \
                self.nodeDataPacketTransmitTimeMs + \
                self.guardIntervalMs + \
                - 2 * (transmitDelayToNode - transmitDelayToPreviousNode)

    def sendAssignedTransmitDelaysToNodes(self):
        for node in self.topology:
            self.modemGateway.send(
                node,
                GATEWAY_ID,
                ID_PAQUET_TDI,
                self.assignedTransmitDelaysMs[node].to_bytes(4, 'big'),
                0,
                0
            )

    def main(self):
        self.modemGateway.addRxCallback(self.packetCallback)
        self.running = True
        while self.running:
            self.receivePacket = {}
            self.receivePacketTimeMs = {}
            self.ReceiveAllDataPacketEvent.clear()
            transmitTimeMs = time.time() * 1000
            self.RequestDataPacket()
            print("Gateway: Waiting for all data packets...")
            if self.ReceiveAllDataPacketEvent.wait(timeout=self.timeoutDataRequestSec):
                print("All data packets received")
                # TODO: handle data packets
            else:
                print("Timeout on data packets reception")
                # TODO: handle timeout
            for nodeId in self.topology:
                if nodeId not in self.receivePacket:
                    # TODO:  if it's the first time we don't receive the data packet of node x
                    # retranmist the tdi packet to node x
                    # else
                    # do nothing
                    # or determine if we should increase the guard interval or timeout
                    continue

                # check if the packet arrived at the expected time
                expectedArrivalTime = transmitTimeMs + \
                                      self.nodeTwoWayTimeOfFlightMs[nodeId] + \
                                      self.assignedTransmitDelaysMs[nodeId]
                actualArrivalTime = self.receivePacketTimeMs[nodeId]
                # TODO: Correct the diff calculation
                diff = abs(actualArrivalTime - expectedArrivalTime)
                print(f"Node {nodeId} error: {diff}")
                if diff > self.jitterThresholdMs:
                    # TODO: Adjust transmit delays
                    self.modemGateway.removeRxCallback(self.packetCallback)
                    self.calculateNodesDelay()
                    self.sendAssignedTransmitDelaysToNodes()
                    self.modemGateway.addRxCallback(self.packetCallback)

            if not self.running:
                break
            # wait for the next period
            elpasedTimeSec = time.time() - (transmitTimeMs / 1000)
            time.sleep(max(self.periodeSec - elpasedTimeSec, 0))
        self.modemGateway.removeRxCallback(self.packetCallback)

    def packetCallback(self, pkt):
        # check if we have received a data packet
        if pkt.header.type == ID_PAQUET_DATA:
            self.receivePacket[pkt.header.src] = pkt
            self.receivePacketTimeMs[pkt.header.src] = time.time() * 1000

            # check if we have received all data packets of the topology
            if len(self.receivePacket) == len(self.topology):
                self.ReceiveAllDataPacketEvent.set()
        else:
            print("Received packet with unknown type")
            printPacket(pkt)
        pass

    def RequestDataPacket(self):
        self.modemGateway.send(
            dst=BROCAST_ADDRESS,
            src=GATEWAY_ID,
            type=ID_PAQUET_REQ_DATA,
            payload=bytearray(),
            status=0,
            dsn=0
        )
