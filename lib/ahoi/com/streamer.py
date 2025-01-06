#
# Copyright 2016-2019
# 
# Bernd-Christian Renner and
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

"""Module for packet encoding and decoding for streaming communication"""

import copy

class Streamer:
  
    DLE = 0x10
    STX = 0x02
    ETX = 0x03
  
    def __init__(self):
        """Initialize streamer."""
        self.flagDLE = False
        self.flagInPacket = False
        self.res = bytearray()
        
    def dec(self, b):
        if not self.flagDLE:
            # last char was no DLE -> simply
            if (b == self.DLE):
                self.flagDLE = True
            elif (self.flagInPacket):
                self.res.append(b)
        else:
            # found a new packet start
            # (DLE STX and not inside another packet)
            if (b == self.STX and not self.flagInPacket):
                self.flagDLE = False
                self.flagInPacket = True

            # found packet end (DLE ETX and inside packet)
            elif (b == self.ETX and self.flagInPacket):
                # reset internal state
                self.flagInPacket = False
                self.flagDLE = False
                tmp = copy.copy(self.res)
                del self.res[:]
                return tmp
            # stuffed DLE (sent char was a DLE)
            elif (b == self.DLE and self.flagInPacket):
                self.flagDLE = False
                self.res.append(b)
            # we ran into something that shouldn't happen
            # -> abort reception
            elif (self.flagInPacket):
                del self.res[:]
                self.flagInPacket = False
                self.flagDLE = False
        
        return None
      
      
    def enc(self, pktbytes):
        res = bytearray([0x10, 0x02]) # start Packet
        for b in pktbytes:
            res.append(b)
            if b == 0x10:
                res.append(b) # stuffing
        res.extend([0x10, 0x03])  # end packet
        return res

# eof
