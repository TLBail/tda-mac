import unittest
from src.Mock.modem_mock_gateway import ModemMockGateway
from src.Mock.node_mock_gateway import NodeMockGateway
import threading
from src.GatewayTDAMAC import GatewayTDAMAC


class TestGateway(unittest.TestCase):
    def setUp(self):
        self.modem = ModemMockGateway()
        self.modem.connect("COM1")
        self.gateway = GatewayTDAMAC(self.modem, [])

    def test_ping_topology_one_node(self):
        # init topology
        self.gateway.topology = [1]
        node = NodeMockGateway(self.modem, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modem.addNode(node)
        # test
        self.gateway.pingTopology()
        assert self.gateway.nodeTwoWayTimeOfFlightMs[1] == 2 * 1e6

    def test_ping_topology_multiple_node(self):
        # init topology
        self.gateway.topology = [1, 2, 3]
        node = NodeMockGateway(self.modem, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modem.addNode(node)
        node2 = NodeMockGateway(self.modem, 2)
        node2.transmitDelay = 1.5
        node2.receptionDelay = 2
        self.modem.addNode(node2)
        node3 = NodeMockGateway(self.modem, 3)
        node3.transmitDelay = 2.5
        node3.receptionDelay = 3
        self.modem.addNode(node3)
        # test
        self.gateway.pingTopology()
        assert self.gateway.nodeTwoWayTimeOfFlightMs[1] == 2 * 1e6
        assert self.gateway.nodeTwoWayTimeOfFlightMs[2] == 3.5 * 1e6
        assert self.gateway.nodeTwoWayTimeOfFlightMs[3] == 5.5 * 1e6

    def test_calculate_assigned_transmissions_delay(self):
        # init topology
        self.gateway.topology = [1, 2, 3]
        node = NodeMockGateway(self.modem, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modem.addNode(node)
        node2 = NodeMockGateway(self.modem, 2)
        node2.transmitDelay = 1
        node2.receptionDelay = 1
        self.modem.addNode(node2)
        node3 = NodeMockGateway(self.modem, 3)
        node3.transmitDelay = 1
        node3.receptionDelay = 1
        self.modem.addNode(node3)

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()

        assert self.gateway.assignedTransmitDelaysMs[1] == 0
        print("self.gateway.assignedTransmitDelaysMs[1]" + str(self.gateway.assignedTransmitDelaysMs[1]))
        assert self.gateway.assignedTransmitDelaysMs[2] != 0
        print("self.gateway.assignedTransmitDelaysMs[2]" + str(self.gateway.assignedTransmitDelaysMs[2]))
        assert self.gateway.assignedTransmitDelaysMs[3] != 0
        print("self.gateway.assignedTransmitDelaysMs[3]" + str(self.gateway.assignedTransmitDelaysMs[3]))

    def test_calculate_assigned_transmissions_delay_with_packet_loss(self):
        # init topology
        self.gateway.topology = [1, 2, 3]
        node = NodeMockGateway(self.modem, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        node.looseNbTransmitPacket = 1
        self.modem.addNode(node)
        node2 = NodeMockGateway(self.modem, 2)
        node2.transmitDelay = 1
        node2.receptionDelay = 1
        node2.looseNbReceivePacket = 1
        self.modem.addNode(node2)
        node3 = NodeMockGateway(self.modem, 3)
        node3.transmitDelay = 1
        node3.receptionDelay = 1
        self.modem.addNode(node3)

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()

        assert self.gateway.assignedTransmitDelaysMs[1] == 0
        print("self.gateway.assignedTransmitDelaysMs[1]" + str(self.gateway.assignedTransmitDelaysMs[1]))
        assert self.gateway.assignedTransmitDelaysMs[2] != 0
        print("self.gateway.assignedTransmitDelaysMs[2]" + str(self.gateway.assignedTransmitDelaysMs[2]))
        assert self.gateway.assignedTransmitDelaysMs[3] != 0
        print("self.gateway.assignedTransmitDelaysMs[3]" + str(self.gateway.assignedTransmitDelaysMs[3]))


if __name__ == '__main__':
    unittest.main()
