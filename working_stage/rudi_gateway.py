#! /usr/bin/env python3
#
# Receive data Using Delay Instruction (RUDI) by Cyprien Aoustin
# Nantes Université, LS2N
#
# Essai de la mise en place d'un protocole MAC rudimentaire - coté gateway
# Objectifs : 
#   - Mesurer le délai de transmission d'un paquet (ToF - Time of Flight)
#   - Réaliser une communication prenant compte du délai de communication
#

from ahoi.modem.modem import Modem
from ahoi.modem.packet import *
import argparse

SPEED_OF_SOUND = 1500   # approx. in meters per second
thread = False          # blocking mode : False // non-blocking mode : True


def portConnect():
    '''Function for selecting the serial port for connection to the modem'''
    parser = argparse.ArgumentParser(
        description="AHOI Modem - RUDI(Gateway) by Cyprien Aoustin",
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

def rxCallback_MAC(pkt):
    '''Callback function for the MAC protocol'''
    # Check if we have received a ranging ACK
    if pkt.header.type == 0x7F and pkt.header.len > 0:
        tof= 0
        print("Réception du paquet ACK de node pour la mesure ToF\n")
        printPacket(pkt)
        # Calcul the ToF value
        for i in range(0,4):
            tof = tof * 256 + pkt.payload[i]
            print(f"\npayload({i}): ", pkt.payload[i])
            print(f"tof({i}): ", tof)
        print(f"ToF: {tof} µs")
        print("Distance: %6.3f cm" % (tof * 1e-4 * SPEED_OF_SOUND))

        # Convert the ToF in a bytearray
        byte_tof= int_to_bytearray(tof)
        print("\nbytearray(tof):", byte_tof)

        # Send the ToF value to the node
        print("\nLancement de la seconde phase, envoi de la mesure Tof à node (send data packet)")
        myModem.send(dst=0x5C, src=0x5B, type=0x7E, payload=byte_tof, status=0)
        
    # Check if we have received a ACK from the node sending back the value of ToF
    if pkt.header.type == 0x7D:
        print("Réception du paquet ACK pour la bonne réception de la mesure ToF")
        tof_recu= int.from_bytes(pkt.payload, byteorder='big')  # Convert the payload received in an integer
        print(f"\nPayload received: {pkt.payload}")
        print(f"Corresponding message: {tof_recu}\n")

def rxCallback_ACK(pkt):
    '''Callback function to print all ACK packets received'''
    if pkt.header.type == 0x7F and pkt.header.len == 0:
        print(pkt.payload)

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
    myModem.addRxCallback(rxCallback_MAC)
    myModem.addRxCallback(rxCallback_ACK)

    # ToF measurement is initiated by sending a data packet with R-Flag - status = 2
    print("Lancement de la procédure de mesure ToF (send ping packet)")
    myModem.send(dst=0x5C, src=0x5B, type=0x7F, status=2)

    # Start the reception of data - argument : thread (set to False by default)
    myModem.receive()

    # Remove the rxCallback functions from the instance
    myModem.removeRxCallback(rxCallback_MAC)
    myModem.removeRxCallback(rxCallback_ACK)

    # Close the connection to the modem
    myModem.close()