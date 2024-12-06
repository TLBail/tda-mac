from .i_modem import IModem
import threading

class GatewayTDAMAC:
    def __init__(self, modemGateway: IModem,  topology: []):
        self.modemGateway: IModem = modemGateway
        self.topology: [] = topology
        self.nodesTimeOfFlight: {} = {}
    def pingTopology(self):
        self.event = threading.Event()
        self.nodesTimeOfFlight = {}
        def modemCallback(pkt):
            # check if we have received a ranging ack
            if pkt.header.type == 0x7F and pkt.header.len > 0:
                # calculate time of flight
                tof = 0
                for i in range(0, 4):
                    tof = tof * 256 + pkt.payload[i]
                self.nodesTimeOfFlight[pkt.header.src] = tof
                # liberate the event to get the next node time of flight
                self.event.set()
        self.modemGateway.addRxCallback(modemCallback)

        for node in self.topology:
            self.modemGateway.send(node, 0, 0x7F, b'\x00\x00\x00', 0)
            self.event.wait()

        self.modemGateway.removeRxCallback(modemCallback)