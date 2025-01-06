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


from ahoi.handlers.SampleHandler import SampleHandler

import numpy as np
import math
from scipy import signal
import matplotlib.pyplot as plt
from matplotlib.mlab import window_none


class SamplePlotHandler(SampleHandler):
    """SamplePlotHandler."""
    
    def __init__(self, nAdc = 12, show = False):
        # TODO
        SampleHandler.__init__(self, nAdc)
        self.show = show
        
        ##self.fig = plt.figure()
        self.fig = None
        #self.fig, self.axs = plt.subplots(nrows=2, ncols=1, figsize=(10,6))  # figsize = (a,b)
        
        #self.__cbar = False
        
        # const
        self.__Fs = 200    # sample frequency (kHz)
        self.__Fmin = 50   # comm. freq. band lower limit (kHz)
        self.__Fmax = 75   # comm. freq. band upper limit (kHz)


    def __del__(self):
        pass
        #if (self.fig):
        #    pyplot.close(self.fig)

    def handlePkt(self, pkt):
        """handle a modem pkt"""
        ret = SampleHandler.handlePkt(self, pkt)
        
        if ret and self.show and self.isComplete():
            self.plot()
            
        return ret
        
        
    def plot(self):
        if self.fig is None:
            self.fig, self.axs = plt.subplots(nrows=2, ncols=1, figsize=(10,6))  # figsize = (a,b)
            self.__cbar = False
        
        #axt = self.axs[0]
        #axb = self.axs[1]
        axt, axb = self.axs.flatten()
      
        # reset plot
        axt.cla()
        axb.cla()
        
        ##
        ## time series
        t =  np.arange(self.numTotal) / self.__Fs
        axt.plot(t, self.data, 'b-')
        
        ## layout
        axt.set_xlabel('time (ms)')
        axt.set_ylabel('relative amplitude')
        axt.axis([t[0], t[-1], -1, 1])
        axt.grid(True)
        
        ##
        ## specgram
        Sxx, F, T, sax = axb.specgram(
            self.data,
            Fs=self.__Fs,
            NFFT=2**8,
            noverlap=2**8//16*15,
            scale_by_freq=False,
            mode='magnitude',
            vmin = -100,
            vmax = 0,
            cmap = plt.get_cmap('plasma'),
            window=window_none) # window=matplotlib.mlab.window_none, 
        
        # layout
        axb.set_xlabel('time (ms)')
        axb.set_ylabel('frequency (kHz)')
        axb.axis([t[0], t[-1], 0, self.__Fs/2])
        axb.grid(True)
        # show colorbar, HACK to prevent it from being drawn each time
        if not self.__cbar:
            self.__cbar = True
            # HACK wild number guessing here
            self.fig.subplots_adjust(bottom=0.1, right=0.82, top=0.9)
            cax = plt.axes([0.85, 0.1, 0.03, 0.36])  # Left Bottom Width Height (?)
            self.fig.colorbar(cax = cax, mappable = sax).set_label('rel. amplitude [dB]')
            #self.fig.colorbar(sax, anchor = (1.0,0.5)).set_label('rel. amplitude [dB]')
        
        ##
        ## plot trigger lines
        trig = (self.numTotal - self.numPost) / self.__Fs
        axt.plot([trig, trig], [-1, 1], 'r--')
        axb.plot([trig, trig], [0, self.__Fs/2], 'r--')
        
        ##
        ## plot freq. band
        axb.plot([t[0], t[-1]], [self.__Fmin, self.__Fmin], 'k--')
        axb.plot([t[0], t[-1]], [self.__Fmax, self.__Fmax], 'k--')
        
        # HACK add a little pause, or plot will not show ...
        plt.draw()
        plt.pause(0.001)
        #plt.ion()
        
        
    def close(self):
        if self.fig:
            plt.close(self.fig)
            self.fig = None


# EOF
