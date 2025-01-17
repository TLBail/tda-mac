import threading
import time
import unittest
from src.Mock.modem_mock_node import ModemMockNode
from src.Mock.modem_mock_gateway import ModemMockGateway
from src.NodeTDAMAC import NodeTDAMAC
from src.Mock.node_mock_gateway import NodeMockGateway, ResponseWithAckForDelay
from lib.ahoi.modem.packet import makePacket
from src.constantes import ID_PAQUET_TDI, ID_PAQUET_DATA
from src.GatewayTDAMAC import GatewayTDAMAC


class TestDelaiEtablie(unittest.TestCase):
    def setUp(self):
        self.modemGateway = ModemMockGateway()
        self.modemGateway.connect("COM1")
        self.modemGateway.receive()
        self.gateway = GatewayTDAMAC(self.modemGateway, [])

    def initScenario1(self):
        print("initScenario1")
        # init mocks
        self.nodeModem = ModemMockNode(1, self.modemGateway)
        self.gateway.topology = [1]
        node = NodeMockGateway(self.modemGateway, 1, lambda node, pkt: self.nodeModem.simulateRx(pkt))
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modemGateway.addNode(node)

        # init node TDAMAC
        self.nodeTDAMAC = NodeTDAMAC(self.nodeModem, 1)

        # init network
        self.nodeModem.connect("COM1")
        self.nodeModem.receive()

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(1.1) # wait for the node to receive the tdi packet
        print("initScenario1 done")

    def initScenario2(self):
        print("initScenario2")
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
        self.nodeTDAMAC = NodeTDAMAC(self.nodeModem, 1)
        self.nodeTDAMAC2 = NodeTDAMAC(self.nodeModem2, 2)
        self.nodeTDAMAC3 = NodeTDAMAC(self.nodeModem3, 3)

        # init network
        self.nodeModem.connect("COM1")
        self.nodeModem.receive()
        self.nodeModem2.connect("COM2")
        self.nodeModem2.receive()
        self.nodeModem3.connect("COM3")
        self.nodeModem3.receive()

        self.gateway.pingTopology()
        self.gateway.calculateNodesDelay()
        self.gateway.sendAssignedTransmitDelaysToNodes()
        time.sleep(1.1) # wait for the node to receive the tdi packet
        print("initScenario2 done")

    def test_send(self):
        self.initScenario1()
        # test
        payload = int(10).to_bytes(4, 'big')
        self.nodeTDAMAC.send(payload)  # add the message to the queue
        assert self.nodeTDAMAC.messageToSendQueue.qsize() == 1

        def StartGatewayMainLoop():
            self.gateway.main()  # send the REQ DATA packet to the nodes

        gatewayThread = threading.Thread(target=StartGatewayMainLoop)
        gatewayThread.start()

        time.sleep(1)  # wait for the gateway to send the REQ packet
        self.gateway.running = False  # stop the gateway
        time.sleep(2)  # wait for the node to answer
        assert self.nodeTDAMAC.messageToSendQueue.qsize() == 0
        gatewayThread.join()
        assert len(self.gateway.receivedPaquets) == 1
        pkt = self.gateway.receivedPaquets[0]
        assert pkt.payload == payload

    def test_send_init_multipleNode(self):
        self.initScenario2()
        # test
        payload = int(10).to_bytes(4, 'big')
        self.nodeTDAMAC.send(payload)  # add the message to the queue

        def StartGatewayMainLoop():
            self.gateway.main()  # send the REQ DATA packet to the nodes

        gatewayThread = threading.Thread(target=StartGatewayMainLoop)
        gatewayThread.start()

        # assert
        time.sleep(1)  # wait for the gateway to send the REQ packet
        self.gateway.running = False  # stop the gateway
        gatewayThread.join() # wait for the node to answer
        assert len(self.gateway.receivedPaquets) == 3
        pkt = self.gateway.receivedPaquets[0]
        assert pkt.payload == payload

    def test_receive_data_packet_of_older_req(self):
        self.initScenario1()
        # on retire le nœud 1 de la topologie
        node: NodeMockGateway = self.modemGateway.nodes[1]
        self.modemGateway.nodes.pop(1)
        # test
        def StartGatewayMainLoop():
            self.gateway.main()  # send the REQ DATA packet to the nodes

        gatewayThread = threading.Thread(target=StartGatewayMainLoop)
        gatewayThread.start()
        # assert
        time.sleep(1)  # wait for the gateway to send the REQ packet
        self.gateway.running = False
        # send the data packet back with the wrong sequence number
        assert self.gateway.dataPaquetSequenceNumber != 0
        node.transmit(makePacket(src=1, dst=0, type=ID_PAQUET_DATA, payload=bytearray(), ack=0, dsn=0))
        time.sleep(self.gateway.timeoutDataRequestSec + 1) # wait for the timeout
        assert len(self.gateway.receivedPaquetOfCurrentReq) == 0

if __name__ == '__main__':
    unittest.main()
