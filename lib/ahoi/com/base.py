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

"""Module for base modem com interfacing."""

import time
import os.path

import ahoi.modem.packet
from ahoi.com.streamer import Streamer


class ModemBaseCom:
  
    def __init__(self, dev = None, cb = None):
        """Initialize serial com."""
        self.dev = dev
        self.rxCallback = cb
        self.streamer = Streamer()
        self.logFile = None
    
    
    def __del__(self):
        """Close connection."""
        self.close()
    
    
    def connect(self, cb = None):
        """Register callback."""
        if cb is not None:
            self.rxCallback = cb


    def close(self):
        """Terminate."""
        self.dev = None
        self.rxCallback = None
        self.logOff()


    def receive(self):
        """Receive a packet."""
        pass
    
    
    def send(self, pkt):
        """Send a packet."""
        pass
      
      
    def processRx(self, rx):
        """handle received bytes and decode packet"""
        for b in rx:
            r = self.streamer.dec(b)
            if r is not None and self.rxCallback is not None:
                pkt = ahoi.modem.packet.byteArrayToPacket(r)
                self.__log(pkt)
                self.rxCallback(pkt)


    def processTx(self, pkt):
        """handle pkt to send (prepare byte stream)"""
        
        # merge header and payload to bytearray
        pktbytes = ahoi.modem.packet.getBytes(pkt)

        # add start, stuffing and end sequence
        tx = self.streamer.enc(pktbytes)
        
        return tx
                        
                        
    def __log(self, pkt):
        """Log packet"""
        if self.logFile is not None and not self.logFile.closed:
            self.logFile.write("{:.3f}".format(time.time()) + " " + ahoi.modem.packet.packet2HexString(pkt) + "\n")
            self.logFile.flush()
            os.fsync(self.logFile.fileno())
      
      
    def logOn(self, file_name=None):
        """Turn logging to file on."""
        if self.logFile is not None:
            if not self.logFile.closed:
                self.logOff()
        try:
            if os.path.exists(file_name):
                # file exists: append first available number to the file name
                i = 1
                file_name2 = file_name + "." + str(i)
                while os.path.exists(file_name2):
                    i = i + 1
                    file_name2 = file_name + "." + str(i)
                print("%s exists, logging to file %s" % (file_name, file_name2))
                file_name = file_name2
            self.logFile = open(file_name, 'w', buffering=1)
        except OSError as e:
            print("Failed to open {}: {}".format(file_name, str(e)))


    def logOff(self):
        """Turn logging to file off."""
        if self.logFile is not None and not self.logFile.closed:
            self.logFile.flush()
            os.fsync(self.logFile.fileno())
            print("Closed logfile {}".format(self.logFile.name))
            self.logFile.close()
            self.logFile = None
    
    
    def scan(self = None):
        return []
    
    
    def scanAndSelect(comType):
        """Find connections and ask user to select."""
        while True:
            conLst = comType.scan()
            
            if len(conLst) == 0:
                choice = input("No connection available. Retry? [Y/n] ")
                if choice.lower() in ["n", "no"]:
                    exit()
            else:
                break
        
        while True:
            print("Available connections:")
            n = 1
            for con in conLst:
                print("{:2}: {:20}".format(n, con))
                n = n + 1
                
            sel = input("Select connection (0 to abort): ")
            try:
                index = int(sel) - 1
                if index < 0:
                    print("Bye bye\n")
                    exit()
                if index >= len(conLst):
                    raise ValueError
                else:
                    sel = conLst[index]
            except ValueError:
                print("Invalid selection")
                continue

            return sel
     
# eof
