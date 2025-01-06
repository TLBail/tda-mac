#
# Copyright 2016-2019
# 
# Bernd-Christian Renner, Jan Heitmann, and
# Hamburg University of Technology (TUHH).
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import struct
import collections

HEADER_FORMAT = 'BBBBBB'
FOOTER_FORMAT = 'BBBBBB'


# PAYLOAD_MAXLEN = 2**LENGTH_SIZE
TYPE_SIZE = 8
ADDRESS_SIZE = 8
MM_TYPE_ACK = (2**TYPE_SIZE) - 1
MM_ADDR_BCAST = (2**ADDRESS_SIZE) - 1

# ACK_TYPE
ACK_NONE = 0
ACK_PLAIN = 1
ACK_RANGE = 2


Header = collections.namedtuple('Header', ['src', 'dst', 'type', 'status', 'dsn', 'len'])
Packet = collections.namedtuple('Packet', ['header', 'payload', 'footer'])
Footer = collections.namedtuple('Footer', ['power', 'rssi', 'biterrors', 'agcMean', 'agcMin', 'agcMax'])


def byteArrayToPacket(rxBytes):
    """Convert received byte array to packet."""
    headLen = len(HEADER_FORMAT)
    # FIXME please do proper error handling
    # if len(rxBytes) < headLen:
    #     # Return an empty packet as error value.
    #     h = bytearray([0, 0, 0, 0, 0, 0])
    #     p = bytearray([])
    #     return Packet(h, p, None)
    headerBytes = rxBytes[0:headLen]
    header = Header(*struct.unpack(HEADER_FORMAT, headerBytes))
    paylen = header.len
    # FIXME please do proper error handling
    # expectedLen = headLen + paylen + (len(FOOTER_FORMAT) if header.type < 0x80 else 0)
    # if len(rxBytes) != expectedLen:
    #     # Length of bytearray is not consistent with value in header field
    #     # Return an empty packet as error value
    #     h = bytearray([0, 0, 0, 0, 0, 0])
    #     p = bytearray([])
    #     return Packet(h, p, None)
    payload = rxBytes[headLen:(headLen+paylen)]
    # FIXME check for difference matching footer length, 0 (no footer), or else (ERROR, invalid)
    if (header.type < 0x80 and
        ((len(rxBytes) - headLen - paylen) == len(FOOTER_FORMAT))):
            footerBytes = rxBytes[(headLen+paylen):]
            footer = Footer(*struct.unpack(FOOTER_FORMAT, footerBytes))
    else:
        footer = None  # Footer(0, 0, 0, 0, 0, 0)
    return Packet(header, payload, footer)


def makePacket(src=0, dst=MM_ADDR_BCAST, type=0, ack=ACK_NONE, dsn=0, payload=bytes()):
    status = ack
    paylen = len(payload)
    header = Header(src, dst, type, status, dsn, paylen)
    footer = None
    pkt = Packet(header, payload, footer)
    return pkt


def getHeaderBytes(pkt):
    headerBytes = bytearray()
    headerBytes += struct.pack(HEADER_FORMAT, *pkt.header)
    return headerBytes


def getFooterBytes(pkt):
    footerBytes = bytearray()
    if hasFooter(pkt):
        footerBytes += struct.pack(FOOTER_FORMAT, *pkt.footer)
    return footerBytes

def hasFooter(pkt):
    return pkt.footer is not None
  
def isCmdType(pkt):
    return pkt.header.type >= 0x80


def getBytes(pkt):
    pktbytes = bytearray()
    pktbytes += struct.pack(HEADER_FORMAT, *pkt.header)
    pktbytes += pkt.payload
    if hasFooter(pkt):
        pktbytes += struct.pack(FOOTER_FORMAT, *pkt.footer)
    return pktbytes
  
  
def packet2HexString(pkt):
    byteArray = getHeaderBytes(pkt) + pkt.payload
    if hasFooter(pkt):
        byteArray += getFooterBytes(pkt)
    return "".join("%02X " % b for b in byteArray)


def printPacket(pkt):
    print("src: ", pkt.header.src, " => dst:", pkt.header.dst)
    print("type: ", hex(pkt.header.type), "seq: ", pkt.header.dsn)
    print("status: {:08b}".format(pkt.header.status))
    print("  ack: ", (pkt.header.status & 0x01))
    print("  rangeack: ", (pkt.header.status & 0x02))
    print("payload: ", pkt.payload)

# eof
