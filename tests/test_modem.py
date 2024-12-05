import threading
import unittest
from unittest.mock import Mock, call, ANY
from src.i_modem import IModem
from src.modem_mock import ModemMock
from src.modem import Modem
from src.node import Node
from ahoi.modem.packet import makePacket, printPacket
import time


def connectModem(modem: IModem) -> None:
    modem.connect("COM1")

def testPacket():
    return makePacket()

    
def onNode1Receive(modem, packet):
    """response with an ACK packet"""
    packet = makePacket()
    modem.simulateRx(packet)

class TestModem(unittest.TestCase):
    def setUp(self):
        self.modem = ModemMock([])
        self.mock = Mock()


    def test_connection(self):
        connectModem(self.modem)
        assert self.modem.connected


    def test_sending_ack(self):
        # test
        self.modem.addRxCallback(self.mock)

        self.modem.connect("COM1")
        self.modem.send(0x5B, 0x5C, 0x7D, b'\x00\x00\x00', 0)

        # on simule la reception d'un packet ACK sur le modem
        packet = makePacket()
        self.modem.simulateRx(packet)

        printPacket(packet)

        # assert
        self.mock.assert_called_once_with(packet)
    

    def test_Rx_callback(self):
        self.event = threading.Event()
        def onModemReceive(packet):
            self.event.set()
        node = Node(self.modem, 1)
        node.transmitDelay = 1
        # test
        self.modem.addRxCallback(onModemReceive)
        start_time = time.time()
        node.transmit(makePacket())
        self.mock.assert_not_called()
        self.event.wait()
        end_time = time.time()
        # assert
        self.assertGreaterEqual(end_time-start_time, 1)

    def test_distance_measurement(self):
        self.event = threading.Event()
        def onNode1Receive(node, packet):
            """payload is the full time of flight because ModemMock does not simulate time of flight"""
            half_tof = int((node.receptionDelay + node.transmitDelay) * 1e6) # Convertir en microsecondes
            tof_payload = half_tof.to_bytes(4, 'big')
            ack_packet = makePacket(
                src=node.adress,  # Source devient la destination (ACK retourne au sender)
                dst=0,
                type=0x7F,  # Type pour les ACK de ranging
                payload=tof_payload
            )
            node.transmit(ack_packet)

        node = Node(self.modem, 1, onNode1Receive)
        node.transmitDelay = 1
        node.receptionDelay = 1
        self.modem.nodes.append(node)
        # test

        def onModemReceive(pkt):
            # asset a payload of
            # check if we have received a ranging ack
            if pkt.header.type == 0x7F and pkt.header.len > 0:
                tof = 0
                for i in range(0, 4):
                    tof = tof * 256 + pkt.payload[i]
                assert tof * 1e-6 == 2
                self.event.set()
            else:
                assert False

        self.modem.addRxCallback(onModemReceive)
        self.modem.connect("COM1")
        self.modem.send(1, 0, 0x7F, b'\x00\x00\x00', 0)
        self.event.wait()

    def test_Tx_delay(self):
        self.event = threading.Event()
        def onModemReceive(modem, packet):
            self.event.set()
        node = Node(self.modem, 1, onModemReceive)
        node.receptionDelay = 1
        self.modem.nodes.append(node)
        # test
        self.modem.connect("COM1")
        self.modem.addRxCallback(self.mock)
        self.modem.send(1, 0, 0, b'\x00\x00\x00', 0)
        # assert
        assert len(node.receivePackets) == 0
        self.event.wait()
        assert len(node.receivePackets) == 1

if __name__ == '__main__':
    unittest.main()