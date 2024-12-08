import threading
import time
import unittest
from src.i_modem import IModem
from src.Mock.modem_mock_node import ModemMockNode
from src.Mock.modem_mock_gateway import ModemMockGateway
from src.NodeTDAMAC import NodeTDAMAC
from src.Mock.node_mock_gateway import NodeMockGateway, ResponseWithAckForDelay
from src.constantes import ID_PAQUET_TDI
from src.GatewayTDAMAC import GatewayTDAMAC


class TestModem(unittest.TestCase):
    def setUp(self):
        self.modemGateway = ModemMockGateway()
        self.modemGateway.connect("COM1")
        self.gateway = GatewayTDAMAC(self.modemGateway, [])

    def test_connection(self):
        # init
        self.nodeModem = ModemMockNode(1, None)
        self.nodeModem.connect("COM1")
        nodeTDAMAC = NodeTDAMAC(self.nodeModem)

        def AssertReceiveTDIPaquet():
            nodeTDAMAC.waitForTDIPacket()
            assert nodeTDAMAC.assignedTransmitDelaysMs == 0

        threading.Thread(target=AssertReceiveTDIPaquet).start()
        time.sleep(0.1)
        self.nodeModem.gatewayModem.send(1, 0, ID_PAQUET_TDI, int(0).to_bytes(4, 'big'), 0, 0)

    def test_mock_gateway(self):
        # init node Modem
        self.nodeModem = ModemMockNode(1, None)
        self.nodeModem.connect("COM1")

        # init mock gateway
        self.gateway.topology = [1]
        node = NodeMockGateway(self.modemGateway, 1, lambda node, pkt: self.nodeModem.simulateRx(pkt))
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)

        # init node TDAMAC
        nodeTDAMAC = NodeTDAMAC(self.nodeModem)
        assert nodeTDAMAC.assignedTransmitDelaysMs == -1

        # test
        self.gateway.pingTopology()

        assert self.gateway.nodeTwoWayTimeOfFlightMs[1] == 2 * 1e6
        self.gateway.calculateNodesDelay()
        assert self.gateway.assignedTransmitDelaysMs[1] == 0
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(3)  # wait for the node to receive the packet
        assert nodeTDAMAC.assignedTransmitDelaysMs == 0

    def test_send(self):
        # init mocks
        self.nodeModem = ModemMockNode(1, self.modemGateway)
        self.gateway.topology = [1]
        node = NodeMockGateway(self.modemGateway, 1, lambda node, pkt: self.nodeModem.simulateRx(pkt))
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)

        # init node TDAMAC
        nodeTDAMAC = NodeTDAMAC(self.nodeModem)

        # init network
        self.nodeModem.connect("COM1")
        self.modemGateway.connect("COM2")

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(1) # wait for the node to receive the tdi packet

        # test
        payload = int(10).to_bytes(4, 'big')
        nodeTDAMAC.send(payload)  # add the message to the queue
        assert nodeTDAMAC.messageToSendQueue.qsize() == 1

        def StartGatewayMainLoop():
            self.gateway.main()  # send the REQ DATA packet to the nodes

        gatewayThread = threading.Thread(target=StartGatewayMainLoop)
        gatewayThread.start()

        time.sleep(1)  # wait for the gateway to send the REQ packet
        self.gateway.running = False  # stop the gateway
        time.sleep(2)  # wait for the node to answer
        assert nodeTDAMAC.messageToSendQueue.qsize() == 0
        gatewayThread.join()
        assert len(self.gateway.receivedPaquets) == 1
        pkt = self.gateway.receivedPaquets[0]
        assert pkt.payload == payload

    def test_send_init_multipleNode(self):
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
        nodeTDAMAC = NodeTDAMAC(self.nodeModem)
        nodeTDAMAC2 = NodeTDAMAC(self.nodeModem2)
        nodeTDAMAC3 = NodeTDAMAC(self.nodeModem3)

        # init network
        self.nodeModem.connect("COM1")
        self.nodeModem2.connect("COM2")
        self.nodeModem3.connect("COM3")
        self.modemGateway.connect("COM4")

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(1) # wait for the node to receive the tdi packet


        # test
        payload = int(10).to_bytes(4, 'big')
        nodeTDAMAC.send(payload)  # add the message to the queue

        def StartGatewayMainLoop():
            self.gateway.main()  # send the REQ DATA packet to the nodes

        gatewayThread = threading.Thread(target=StartGatewayMainLoop)
        gatewayThread.start()

        # assert
        time.sleep(1)  # wait for the gateway to send the REQ packet
        self.gateway.running = False  # stop the gateway
        time.sleep(2)  # wait for the node to answer
        gatewayThread.join()
        assert len(self.gateway.receivedPaquets) == 1
        pkt = self.gateway.receivedPaquets[0]
        assert pkt.payload == payload



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
        nodeTDAMAC = NodeTDAMAC(self.nodeModem)
        nodeTDAMAC2 = NodeTDAMAC(self.nodeModem2)
        nodeTDAMAC3 = NodeTDAMAC(self.nodeModem3)

        # init network
        self.nodeModem.connect("COM1")
        self.nodeModem2.connect("COM2")
        self.nodeModem3.connect("COM3")
        self.modemGateway.connect("COM4")

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()
        # test
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(3)
        # assert
        assert nodeTDAMAC.assignedTransmitDelaysMs == 0
        assert nodeTDAMAC2.assignedTransmitDelaysMs == \
            self.gateway.guardIntervalMs + self.gateway.nodeDataPacketTransmitTimeMs
        assert nodeTDAMAC3.assignedTransmitDelaysMs == \
            nodeTDAMAC2.assignedTransmitDelaysMs + self.gateway.guardIntervalMs + self.gateway.nodeDataPacketTransmitTimeMs





if __name__ == '__main__':
    unittest.main()
