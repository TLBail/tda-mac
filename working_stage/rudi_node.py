#! /usr/bin/env python3
#
# Receive data Using Delay Instruction (RUDI) by Cyprien Aoustin
# Nantes Université, LS2N
#
# Essai de la mise en place d'un protocole MAC rudimentaire - côté node
# Objectifs : 
#   - Mesurer le délai de transmission d'un paquet (ToF - Time of Flight)
#   - Réaliser une communication prenant compte du délai de communication
#

from ahoi.modem.modem import Modem
from ahoi.modem.packet import *
import argparse
import time

thread = False  # blocking mode for the receive function : False // non-blocking mode : True


def portConnect():
    '''Function for selecting the serial port for connection to the modem'''
    parser = argparse.ArgumentParser(
        description="AHOI Modem - RUDI(Sensor Node) by Cyprien Aoustin",
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

def int_to_bytearray(value):
    '''Function to convert an integer into a bytearray'''
    value_byte= value.to_bytes(3, byteorder='big') # Convert the value into bytes -> length=3 (tof<2^15)
    value_bytearray= bytearray(value_byte) # Convert the bytes_value into a bytearray
    return value_bytearray

def rxCallback_wait(pkt):
    '''Callback function for managing protocol return messages'''
    # Check if a message has been received with the ToF value
    if pkt.header.type == 0x7E:
        printPacket(pkt)
        print("\nPayload received:", pkt.payload)
        tof_recu= int.from_bytes(pkt.payload, byteorder='big') # Convert the received payload into an integer

        print(f"ToF recu: {tof_recu} µs")
        message_tof= int_to_bytearray(tof_recu) # Convert the ToF value into a bytearray
        print("ACK to send to the gateway:",message_tof)

        # Init the waiting value and start the delay
        tof_us= tof_recu*1e-6
        tof_s= tof_us+1 # Add delay to the tof (easier to see the delay)
        time.sleep(tof_s)

        # Send the ACK with the ToF value received to the gateway
        print("\nEnvoi de la confirmation de réception de la mesure ToF (send ACK data packet)")
        myModem.send(dst=0x5B, src=0x5C, type=0x7D, payload=message_tof, status=0)

if __name__ == "__main__":
    # Create modem instance
    myModem = Modem()

    # Select the modem connection port
    serialPort= portConnect().dev

    # Connect the modem through the serial port
    myModem.connect(serialPort)
    dev = myModem.com.dev       # What does this line do ?
    myModem.setTxEcho(True)
    myModem.setRxEcho(True)

    # Add the rxCallback functions in the instance
    myModem.addRxCallback(rxCallback_wait)

    # Start the reception of data - possible argument : thread (set to False by default)
    myModem.receive()

    # Remove the rxCallback functions from the instance
    myModem.removeRxCallback(rxCallback_wait)

    # Close the connection to the modem
    myModem.close()