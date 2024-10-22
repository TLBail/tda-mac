#! /usr/bin/env python3
#
# AHOI Protocol Interface (ahoiPI) by Cyprien Aoustin
# Nantes Université, LS2N
#

from ahoi.modem.modem import Modem
import argparse
import time


SPEED_OF_SOUND = 1500  # approx. in meters per second


def rxCallback(pkt):
    # check if we have received a ranging ack
    if pkt.header.type == 0x7F and pkt.header.length > 0:
        tof = 0
        for i in range(0,4):
            tof = tof * 256 + pkt.payload[i]
        print("distance: %6.1f" % (tof * 1e-6 * SPEED_OF_SOUND))

def portConnect():
    parser = argparse.ArgumentParser(
        description="AHOI Modem - AhoiPI by Cyprien Aoustin",
        epilog="""\
            NOTE: no security measures are implemented.
            Input is not validated.""")

    parser.add_argument(
        nargs='?',
        type=str,
        default=None,
        dest='dev',
        metavar='device',
        help='device name with connected ahoi modem')

    args = parser.parse_args()
    return args

# def setDate():
    
    
# time.time() temps depuis epoch en secondes            float
# time.time_ns() temps depuis epoch en nanosecondes     int
# time.sleep() suspend l'exécution pendant X secondes   float (arg)


if __name__ == "__main__":

    serialPort= portConnect().dev

    # create modem instance and connect
    myModem = Modem()
    myModem.connect(serialPort)
    myModem.setTxEcho(True)
    myModem.setRxEcho(True)

    # myModem.send(dst=0xFF, payload=bytearray(8), status=0, dsn=10)

    # myModem.addRxCallback(rxCallback)
    # myModem.removeRxCallback(rxCallback)

    myModem.close()