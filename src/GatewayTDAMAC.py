from .i_modem import IModem
import threading
from typing import Dict


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

    def pingTopology(self):
        self.event = threading.Event()
        self.nodesInfo = {}

        def modemCallback(pkt):
            # check if we have received a ranging ack
            if pkt.header.type == 0x7F and pkt.header.len > 0:
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
                self.modemGateway.send(node, 0, 0x7F, int(0).to_bytes(4, 'big'), 0)
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
