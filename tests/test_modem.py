import threading
import unittest
from unittest.mock import Mock
from src.i_modem import IModem
from src.Mock.modem_mock_gateway import ModemMockGateway
from src.Mock.node_mock_gateway import NodeMockGateway
from ahoi.modem.packet import makePacket, printPacket
from src.constantes import FLAG_R
import time


class TestModem(unittest.TestCase):
    def setUp(self):
        self.modem = ModemMockGateway()
        self.mock = Mock()

    def test_connection(self):
        self.modem.connect("COM1")
        assert self.modem.connected

    def test_sending_ack(self):
        # init
        self.modem.addRxCallback(self.mock)
        self.modem.connect("COM1")

        #test
        # on simule la reception d'un packet ACK sur le modem
        packet = makePacket()
        self.modem.simulateRx(packet)

        printPacket(packet)

        # assert
        self.mock.assert_called_once_with(packet)

    def test_Rx_callback(self):
        event = threading.Event()

        def onModemReceive(packet):
            event.set()

        node = NodeMockGateway(self.modem, 1)
        node.transmitDelay = 1
        # test
        self.modem.addRxCallback(onModemReceive)
        start_time = time.time()
        node.transmit(makePacket())
        self.mock.assert_not_called()
        event.wait()
        end_time = time.time()
        # assert
        self.assertGreaterEqual(end_time - start_time, 1)

    def test_distance_measurement(self):
        node = NodeMockGateway(self.modem, 1)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modem.addNode(node)
        event = threading.Event()

        def onModemReceive(pkt):
            # asset a payload of
            # check if we have received a ranging ack
            if pkt.header.type == 0x7F and pkt.header.len > 0:
                tof = 0
                for i in range(0, 4):
                    tof = tof * 256 + pkt.payload[i]
                assert tof * 1e-6 == 2
                event.set()
            else:
                assert False

        self.modem.addRxCallback(onModemReceive)
        self.modem.connect("COM1")
        # test
        self.modem.send(dst=1, src=0, type=0x7F, payload=bytearray(), status=FLAG_R)
        event.wait()

    def test_Tx_delay(self):
        event = threading.Event()

        def onModemReceive(modem, packet):
            event.set()

        node = NodeMockGateway(self.modem, 1, onModemReceive)
        node.receptionDelay = 1
        self.modem.addNode(node)
        # test
        self.modem.connect("COM1")
        self.modem.addRxCallback(self.mock)
        self.modem.send(1, 0, 0, b'\x00\x00\x00', 0)
        # assert
        assert len(node.receivePackets) == 0
        event.wait()
        assert len(node.receivePackets) == 1

    def test_multiple_node_broadcast(self):
        self.modem.connect("COM1")
        event = threading.Event()

        def onNode1Receive(node, packet):
            event.set()

        node = NodeMockGateway(self.modem, 1, onNode1Receive)
        node.receptionDelay = 1
        self.modem.addNode(node)
        event2 = threading.Event()

        def onNode2Receive(node, packet):
            event2.set()

        node2 = NodeMockGateway(self.modem, 2, onNode2Receive)
        node2.receptionDelay = 2
        self.modem.addNode(node2)
        event3 = threading.Event()

        def onNode3Receive(node, packet):
            event3.set()

        node3 = NodeMockGateway(self.modem, 3, onNode3Receive)
        node3.receptionDelay = 3
        self.modem.addNode(node3)

        # test
        self.modem.send(255, 0, 0, b'\x00\x00\x00', 0)
        # assert all nodes received the packet
        event.wait()
        event2.wait()
        event3.wait()

    def test_delay_on_multipleNodeMock(self):
        self.modem.connect("COM1")
        event = threading.Event()

        def onNode1Receive(node, packet):
            event.set()
            self.timeAtReceptionNode1 = time.time()

        node = NodeMockGateway(self.modem, 1, onNode1Receive)
        node.receptionDelay = 1
        self.modem.addNode(node)
        event2 = threading.Event()

        def onNode2Receive(node, packet):
            event2.set()
            self.timeAtReceptionNode2 = time.time()

        node2 = NodeMockGateway(self.modem, 2, onNode2Receive)
        node2.receptionDelay = 2
        self.modem.addNode(node2)
        event3 = threading.Event()

        def onNode3Receive(node, packet):
            event3.set()
            self.timeAtReceptionNode3 = time.time()

        node3 = NodeMockGateway(self.modem, 3, onNode3Receive)
        node3.receptionDelay = 3
        self.modem.addNode(node3)

        # test
        self.modem.send(255, 0, 0, b'\x00\x00\x00', 0)
        # assert all nodes received the packet
        event.wait()
        event2.wait()
        event3.wait()

        # assert delays are respected
        assert self.timeAtReceptionNode1 < self.timeAtReceptionNode2
        assert self.timeAtReceptionNode2 < self.timeAtReceptionNode3


if __name__ == '__main__':
    unittest.main()
