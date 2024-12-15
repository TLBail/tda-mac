import unittest
from src.Mock.modem_mock_gateway import ModemMockGateway
from src.Mock.node_mock_gateway import NodeMockGateway
from src.GatewayTDAMAC import GatewayTDAMAC
from src.NodeTDAMAC import NodeTDAMAC
from src.Mock.modem_mock_node import ModemMockNode
import time


class TestMiseEnPlaceDelai(unittest.TestCase):
    def setUp(self):
        self.modemGateway = ModemMockGateway()
        self.modemGateway.connect("COM1")
        self.modemGateway.receive()
        self.gateway = GatewayTDAMAC(self.modemGateway, [])
    def test_ping_topology_one_node(self):
        # init topology
        self.gateway.topology = [1]
        node = NodeMockGateway(self.modemGateway, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)
        # test
        self.gateway.pingTopology()
        assert self.gateway.nodeTwoWayTimeOfFlightUs[1] == 2 * 1e6

    def test_ping_topology_multiple_node(self):
        # init topology
        self.gateway.topology = [1, 2, 3]
        node = NodeMockGateway(self.modemGateway, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)
        node2 = NodeMockGateway(self.modemGateway, 2)
        node2.transmitDelay = 1.5
        node2.receptionDelay = 2
        self.modemGateway.addNode(node2)
        node3 = NodeMockGateway(self.modemGateway, 3)
        node3.transmitDelay = 2.5
        node3.receptionDelay = 3
        self.modemGateway.addNode(node3)
        # test
        self.gateway.pingTopology()
        assert self.gateway.nodeTwoWayTimeOfFlightUs[1] == 2 * 1e6
        assert self.gateway.nodeTwoWayTimeOfFlightUs[2] == 3.5 * 1e6
        assert self.gateway.nodeTwoWayTimeOfFlightUs[3] == 5.5 * 1e6

    def test_calculate_assigned_transmissions_delay(self):
        # init topology
        self.gateway.topology = [1, 2, 3]
        node = NodeMockGateway(self.modemGateway, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)
        node2 = NodeMockGateway(self.modemGateway, 2)
        node2.transmitDelay = 1
        node2.receptionDelay = 1
        self.modemGateway.addNode(node2)
        node3 = NodeMockGateway(self.modemGateway, 3)
        node3.transmitDelay = 1
        node3.receptionDelay = 1
        self.modemGateway.addNode(node3)

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()

        assert self.gateway.assignedTransmitDelaysUs[1] == 0
        print("self.gateway.assignedTransmitDelaysMs[1]" + str(self.gateway.assignedTransmitDelaysUs[1]))
        assert self.gateway.assignedTransmitDelaysUs[2] != 0
        print("self.gateway.assignedTransmitDelaysMs[2]" + str(self.gateway.assignedTransmitDelaysUs[2]))
        assert self.gateway.assignedTransmitDelaysUs[3] != 0
        print("self.gateway.assignedTransmitDelaysMs[3]" + str(self.gateway.assignedTransmitDelaysUs[3]))

    def test_calculate_assigned_transmissions_delay_with_packet_loss(self):
        # init topology
        self.gateway.topology = [1, 2, 3]
        node = NodeMockGateway(self.modemGateway, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        node.looseNbTransmitPacket = 1
        self.modemGateway.addNode(node)
        node2 = NodeMockGateway(self.modemGateway, 2)
        node2.transmitDelay = 1
        node2.receptionDelay = 1
        node2.looseNbReceivePacket = 1
        self.modemGateway.addNode(node2)
        node3 = NodeMockGateway(self.modemGateway, 3)
        node3.transmitDelay = 1
        node3.receptionDelay = 1
        self.modemGateway.addNode(node3)

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()

        assert self.gateway.assignedTransmitDelaysUs[1] == 0
        print("self.gateway.assignedTransmitDelaysMs[1]" + str(self.gateway.assignedTransmitDelaysUs[1]))
        assert self.gateway.assignedTransmitDelaysUs[2] != 0
        print("self.gateway.assignedTransmitDelaysMs[2]" + str(self.gateway.assignedTransmitDelaysUs[2]))
        assert self.gateway.assignedTransmitDelaysUs[3] != 0
        print("self.gateway.assignedTransmitDelaysMs[3]" + str(self.gateway.assignedTransmitDelaysUs[3]))


    def test_send_assigned_transmissions_delay(self):
        # init node Modem
        self.nodeModem = ModemMockNode(1, None)
        self.nodeModem.connect("COM1")
        self.nodeModem.receive()

        # init mock gateway
        self.gateway.topology = [1]
        node = NodeMockGateway(self.modemGateway, 1, lambda node, pkt: self.nodeModem.simulateRx(pkt))
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)

        # init node TDAMAC
        nodeTDAMAC = NodeTDAMAC(self.nodeModem, 1)
        assert nodeTDAMAC.assignedTransmitDelaysUs == -1

        # test
        self.gateway.pingTopology()

        assert self.gateway.nodeTwoWayTimeOfFlightUs[1] == 2 * 1e6
        self.gateway.calculateNodesDelay()
        assert self.gateway.assignedTransmitDelaysUs[1] == 0
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(3)  # wait for the node to receive the packet
        assert nodeTDAMAC.assignedTransmitDelaysUs == 0

    def test_send_tdi_packet_to_multiple_nodes(self):
        # init mocks
        # gateway
        self.gateway.topology = [1, 2, 3]
        # node 1
        self.nodeModem = ModemMockNode(1, self.modemGateway)
        node = NodeMockGateway(self.modemGateway, 1, lambda node, pkt: self.nodeModem.simulateRx(pkt))
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)
        # node 2
        self.nodeModem2 = ModemMockNode(2, self.modemGateway)
        node = NodeMockGateway(self.modemGateway, 2, lambda node, pkt: self.nodeModem2.simulateRx(pkt))
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)
        # node 3
        self.nodeModem3 = ModemMockNode(3, self.modemGateway)
        node = NodeMockGateway(self.modemGateway, 3, lambda node, pkt: self.nodeModem3.simulateRx(pkt))
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)

        # init node TDAMAC
        nodeTDAMAC = NodeTDAMAC(self.nodeModem, 1)
        nodeTDAMAC2 = NodeTDAMAC(self.nodeModem2, 2)
        nodeTDAMAC3 = NodeTDAMAC(self.nodeModem3, 3)

        # init network
        self.nodeModem.connect("COM1")
        self.nodeModem.receive()
        self.nodeModem2.connect("COM2")
        self.nodeModem2.receive()
        self.nodeModem3.connect("COM3")
        self.nodeModem3.receive()
        self.modemGateway.connect("COM4")
        self.modemGateway.receive()

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()
        # test
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(3)
        # assert
        assert nodeTDAMAC.assignedTransmitDelaysUs == 0
        assert nodeTDAMAC2.assignedTransmitDelaysUs == \
               self.gateway.guardIntervalUs + self.gateway.nodeDataPacketTransmitTimeUs
        assert nodeTDAMAC3.assignedTransmitDelaysUs == \
               nodeTDAMAC2.assignedTransmitDelaysUs + self.gateway.guardIntervalUs + self.gateway.nodeDataPacketTransmitTimeUs




if __name__ == '__main__':
    unittest.main()
