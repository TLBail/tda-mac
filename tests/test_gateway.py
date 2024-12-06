import unittest
from src.i_modem import IModem
from src.modem_mock import ModemMock
from src.modem import Modem
from src.node import Node, ResponseWithAckForDelay
import threading
from lib.ahoi.modem.packet import makePacket
from src.GatewayTDAMAC import GatewayTDAMAC


class TestGateway(unittest.TestCase):
    def setUp(self):
        self.modem = ModemMock([])
        self.modem.connect("COM1")
        self.gateway = GatewayTDAMAC(self.modem, [1])

    def test_ping_topology(self):
        # init topology
        self.event = threading.Event()
        node = Node(self.modem, 1, ResponseWithAckForDelay)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modem.nodes.append(node)
        # test
        self.gateway.pingTopology()
        assert self.gateway.nodesTimeOfFlight[1] == 2 * 1e6


if __name__ == '__main__':
    unittest.main()
