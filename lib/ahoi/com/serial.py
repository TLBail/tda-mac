#
# Copyright 2016-2020
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

"""Module for serial modem com interfacing."""

#import sys
import time

import serial
from serial.tools.list_ports import comports

from ahoi.com.base import ModemBaseCom


class ModemSerialCom(ModemBaseCom):
  
    def __init__(self, dev = None, cb = None):
        """Initialize serial com."""
        super().__init__(dev, cb)
        self.com = None
        self.txDelay = 0.1
    
    
    def __del__(self):
        """Close connection."""
        self.close()
    
    
    def connect(self, cb = None):
        """Open the serial connection."""
        if cb is not None:
            self.rxCallback = cb
            
        try:
            print("Using serial connection at %s" % self.dev)
            self.com = serial.Serial(
                port = self.dev,
                baudrate = 115200,
                parity = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                bytesize = serial.EIGHTBITS,
                timeout = 0.1
            )
        except:
            print("ERROR: cannot connect to %s!" % self.dev)
            exit()
            
            
    def reconnect(self):
        self.com.open()
        self.__keepAlive = False
    
    
    def disconnect(self):
        self.__keepAlive = True
        self.com.flush()
        self.com.cancel_read()
        self.com.close()


    def close(self):
        """Terminate."""
        try:
            self.com.close()
        except:
            pass
          
        super().close()
        

    def receive(self):
        """Receive and decode serial packet"""
        self.__keepAlive = False
        while self.com and (self.com.is_open or self.__keepAlive):
            try:
                rx = self.com.read(self.com.in_waiting or 1)
            except:
                if not self.__keepAlive:
                    print("ERROR: Cannot receive packet, serial connection not open")
                    return
            
            super().processRx(rx)
            
        return


    def scanAndSelect():
        # TODO any better solution possible?
        return ModemBaseCom.scanAndSelect(ModemSerialCom)


    def send(self, pkt):
        """Send a packet."""
        if not self.com or not self.com.is_open:
            print("ERROR: Cannot send packet, serial connection not open")
            return
    
        # send encoded data
        tx = super().processTx(pkt)
        self.com.write(tx)

        time.sleep(self.txDelay)
    

    def scan():
        """find ports and ask user."""
        ports = []
        for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
            ports.append(port)
            
        return ports
        
# eof
