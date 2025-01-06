#
# Copyright 2016-2020
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

"""Handler to visualize sample data from modem."""


from ahoi.handlers.Handler import Handler

import math

class SampleHandler(Handler):
    """SampleHandler."""
    
    def __init__(self, nAdc = 12):
        # TODO
        Handler.__init__(self)
        self.src = -1
        self.data = []
        self.numTotal = 0
        self.numPost = 0
        self.adcRange = pow(2, nAdc)
        
        # const
        self.__Fs = 200    # sample frequency (kHz)
        self.__Fmin = 50   # comm. freq. band lower limit (kHz)
        self.__Fmax = 75   # comm. freq. band upper limit (kHz)

    def __del__(self):
        pass

    def handlePkt(self, pkt):
        """handle a modem pkt"""
        #Handler.handlePkt(self, pkt) # FIXME needed?
        if pkt.header.type != 0xA0 or pkt.header.len == 0:
            return False
        
        if pkt.header.len == 5:
            self.src = pkt.header.src
            self.numTotal = pkt.payload[1] * 256 + pkt.payload[2]
            self.numPost = pkt.payload[3] * 256 + pkt.payload[4] 
            self.data = []
            
        else:
            nb = math.floor(pkt.header.len / 2)
            if (len(self.data) + nb <= self.numTotal):
                for i in range(0, nb):
                    # TODO convert ADC range to [-2^(N-1),2^(N-1)[
                    v = pkt.payload[2*i] * 256 + pkt.payload[2*i+1];
                    if (v >= 2**15):
                        v = v - 2**16
                    self.data.append(v / 2**14)
                    
        return True


    def isComplete(self):
        return self.numTotal > 0 and len(self.data) == self.numTotal


# EOF
