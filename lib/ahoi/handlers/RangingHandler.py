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

"""Handler to visualize distances."""


from ahoi.handlers.Handler import Handler
from collections import deque
import math


class RangingHandler(Handler):
    """RangingHandler."""
    
    def __init__(self, c = 1490, n = 100):
        # TODO
        Handler.__init__(self)
        self.seq = deque()
        self.dist = deque()
        self.c = c
        self.n = n
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1,1,1)

    def __del__(self):
        pass
        #if (self.fig):
        #    pyplot.close(self.fig)

    def handlePkt(self, pkt):
        """handle a modem pkt"""
        #Handler.handlePkt(self, pkt) # FIXME needed?
        if (pkt.header.type != 0x7F or pkt.header.len != 16):
            return False
        
        # sequence number (handle wraps)
        seq = pkt.header.seqno
        if len(self.seq) > 0 and self.seq[-1] >= seq:
            seq = math.ceil(self.seq[-1] / 256) * 256 + seq
        
        # tof
        tof = 0
        for i in range(0,4):
            tof = tof * 256 + pkt.payload[i]
        print("distance: %6.1f" % (tof))
        
        # append
        self.seq.append( seq )
        self.dist.append( tof * 1e-6 * self.c )
        
        if (len(self.dist) > self.n):
            self.seq.popleft()
            self.dist.popleft()
            
        self.plot()
        return True
        
        
    def plot(self):
        # reset plot
        self.ax.clear()
        
        ## plot data
        self.ax.plot(self.seq, self.dist, 'bx-')
        
        ## layout
        self.ax.set_xlabel('sample')
        self.ax.set_ylabel('distance (m)')
        if self.seq.len >= self.n:
            ar = self.n
            al = 1
        else:
            ar = self.seq[-1]
            al = self.seq[-1] - self.n + 1
        ymax = math.ceil(self.dist.max() / 10) * 10
        self.ax.axis([al, ar, 0, ymax])
        self.ax.grid(True);
        
        # HACK add a little pause, or plot will not show ...
        plt.pause(0.001)
        
        
    def close(self):
        if (self.fig):
            plt.close(self.fig)      


# EOF
