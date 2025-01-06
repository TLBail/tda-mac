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

"""Module for modem."""

import time
import string
import os.path
import threading
import subprocess

from ahoi.modem.packet import makePacket
from ahoi.modem.packet import packet2HexString
from ahoi.modem.packet import isCmdType

from ahoi.com.base import ModemBaseCom
from ahoi.com.serial import ModemSerialCom
from ahoi.com.socket import ModemSocketCom


class Modem():
    """ahoi Acoustic Underwater Modem."""

    def __init__(self):
        """Initialize modem."""
        self.timeout = 1.0  # timeout for response to any command
        self.blocking = False
        self.seqNumber = 0
        self.rxCallbacks = []
        self.rxHandlers = []
        #self.logFile = None
        self.rxThread = None
        self.echoTx = False
        self.echoRx = False
        self.com = None
        
        # consts
        self.MAX_PEAKWINLEN = 640 # us

    def __del__(self):
        """Close all files and connections before termination."""
        self.close()
        
    def connect(self, dev = None):
        if self.com:
            self.com.close()
      
        if dev:
            if isinstance(dev, ModemBaseCom):
                self.com = dev
            elif isinstance(dev, str):
                if dev.startswith("tcp@"):
                    dev = dev[4:]
                    tcpparts = dev.split(':')
                    if len(tcpparts) == 1:
                        self.com = ModemSocketCom(tcpparts[0], None)
                    else:
                        self.com = ModemSocketCom(tcpparts[0], tcpparts[1])
                else:
                    self.com = ModemSerialCom(dev)
            else:
                pass
               #raise( ... ) TODO
        else:
            dev = ModemSerialCom.scanAndSelect()
            self.com = ModemSerialCom(dev)
        
        self.com.connect(self.__receivePacket)
        
    # activate blocking mode
    def setModeBlocking(self, block = True):
        #self.timeout = to
        self.blocking = block

    def addRxCallback(self, cb):
        """Add a function to be called on rx pkt."""
        self.rxCallbacks.append(cb)

    def removeRxCallback(self, cb):
        """Remove a function to be called on rx pkt."""
        if cb in self.rxCallbacks:
            self.rxCallbacks.remove(cb)
        
    def addRxHandler(self, cb, type=None):
        """Add a handler (class) to be called on rx pkt."""
        # add filter for packet types
        self.rxHandlers.append(cb)
        
    def removeRxHandler(self, h, type=None):
       """Remove a handler (class) to be called on rx pkt."""
       if h in self.rxHandlers:
           self.rxHandlers.remove(h)

    def close(self):
        """Terminate."""
        if self.com:
            self.com.close()
        
        #if self.logFile is not None:
        #    self.logFile.close()
        
        if self.rxThread is not None:
            self.rxThread.join()


    def __receivePacket(self, pkt):
        # echoing
        if self.echoRx:
            self.__printRxRaw(pkt)
        
        # logging
#        if self.logFile is not None and not self.logFile.closed:
#            self.logFile.write("{:.3f}".format(time.time()) + " " + packet2HexString(pkt) + "\n")
#            self.logFile.flush()
#            os.fsync(self.logFile.fileno())
        
        # FIXME right position?
        self.__waitResp = False  # received packet, unblock
        
        for f in self.rxCallbacks:
            f(pkt)
        for h in self.rxHandlers:
            h.handlePkt(pkt)
    
    
    def receive(self, thread = False):
        if not thread:
            self.com.receive()
        else:
            self.rxThread = threading.Thread(target = self.com.receive)
            self.rxThread.start()


    def send(self, src, dst, type, payload=bytearray(), status=None, dsn=None):
        """Send a packet."""
        if dsn is None or dsn > 255:
            dsn = self.seqNumber

        pkt = makePacket(src, dst, type, status, dsn, payload)
        return self.__sendPacket(pkt)

    def __sendPacket(self, pkt):
        """Send a packet."""
        # output
        if self.echoTx:
            output = "TX@"
            output += "{:.3f}".format(time.time())
            output += " "
            output += packet2HexString(pkt)
            print(output)
            # packet.printPacket(pkt)
        
        # hand over to com
        self.com.send(pkt)  # FIXME how to handle delays with different connections?

        # manage seqnos
        self.seqNumber = (self.seqNumber + 1) % 256
        
        # FIXME how to handle delays with different connections?
        if self.blocking and isCmdType(pkt):
            self.__waitResp = True
            n = self.timeout / 10e-3
            while n > 0 and self.__waitResp:
                time.sleep(10e-3)
                n = n - 1
              
            if n == 0 and self.__waitResp:
                print("timeout")
                # FIXME through exception or so, if not received?
        #else:
        #    time.sleep()
        
        return 0 # HOTFIX to avoid mosh showing improper parameter use for commands
        #return not self.__waitResp

    def getVersion(self):
        """Get firmware version."""
        pkt = makePacket(type=0x80)
        return self.__sendPacket(pkt)

    def getBatVoltage(self):
        """Get Battery Voltage."""
        pkt = makePacket(type=0x85)
        return self.__sendPacket(pkt)

    def getConfig(self):
        """Get modem config."""
        pkt = makePacket(type=0x83)
        return self.__sendPacket(pkt)

    def getPowerLevel(self):
        """Get power level."""
        pkt = makePacket(type=0xB8)
        return self.__sendPacket(pkt)

    def getPacketStat(self):
        """Get packet statistics."""
        pkt = makePacket(type=0xC0)
        return self.__sendPacket(pkt)

    def clearPacketStat(self):
        """Clear packet statistics."""
        pkt = makePacket(type=0xC1)
        return self.__sendPacket(pkt)

    def getSyncStat(self):
        """Get sync statistics."""
        pkt = makePacket(type=0xC2)
        return self.__sendPacket(pkt)

    def clearSyncStat(self):
        """Clear sync statistics."""
        pkt = makePacket(type=0xC3)
        return self.__sendPacket(pkt)

    def getSfdStat(self):
        """Get sfd statistics."""
        pkt = makePacket(type=0xC4)
        return self.__sendPacket(pkt)

    def clearSfdStat(self):
        """Clear sfd statistics."""
        pkt = makePacket(type=0xC5)
        return self.__sendPacket(pkt)

    def freqBandsNum(self, num=None):
        """Get or Set number of freq bands."""
        data = bytearray()
        if num is not None:
            data = num.to_bytes(1, 'big')
        pkt = makePacket(type=0x90, payload=data)
        return self.__sendPacket(pkt)

    def freqBands(self):
        """Get or Set freq bands."""
        print("WARNING: No setter for freqBands implemented.")
        data = bytearray()
        pkt = makePacket(type=0x91, payload=data)
        return self.__sendPacket(pkt)

    def freqCarrierNum(self, num=None):
        """Get or Set number of carriers."""
        data = bytearray()
        if num is not None:
            data = num.to_bytes(1, 'big')
        pkt = makePacket(type=0x92, payload=data)
        return self.__sendPacket(pkt)

    def freqCarriers(self):
        """Get or Set carriers."""
        print("WARNING: No setter for freqCarriers implemented.")
        data = bytearray()
        pkt = makePacket(type=0x93, payload=data)
        return self.__sendPacket(pkt)

    def rangeDelay(self, delay=None):
        """Set delay for ranging answer."""
        data = bytearray()
        if delay is not None:
            data = delay.to_bytes(4, 'big')
        pkt = makePacket(type=0xA8, payload=data)
        return self.__sendPacket(pkt)

    def rxThresh(self, thresh=None):
        """Get or Set rx threshold."""
        data = bytearray()
        if thresh is not None:
            data = thresh.to_bytes(1, 'big')
        pkt = makePacket(type=0x94, payload=data)
        return self.__sendPacket(pkt)

    def rxLevel(self):
        """Get rx level."""
        pkt = makePacket(type=0xB9)
        return self.__sendPacket(pkt)

    def bitSpread(self, chips=None):
        """Get or Set bit spread (number of chips)."""
        data = bytearray()
        if chips is not None:
            data = chips.to_bytes(1, 'big')
        pkt = makePacket(type=0x95, payload=data)
        return self.__sendPacket(pkt)

    # DEPRECATED
    def spreadCode(self, length=None):
        self.bitSpread(length)

    def filterRaw(self, stage=None, level=None):
        """Get or Set gain of RX board."""
        data = bytearray()
        if stage is not None and level is not None:
            data += stage.to_bytes(1, 'big')
            # data += level.to_bytes(1, 'big')
            data += bytearray.fromhex(level)
        pkt = makePacket(type=0x96, payload=data)
        return self.__sendPacket(pkt)

    def syncLen(self, txlen=None, rxlen=None):
        """Get or Set length of sync."""
        data = bytearray()
        if txlen is not None and rxlen is not None:
            data += int(txlen).to_bytes(1, 'big')
            data += int(rxlen).to_bytes(1, 'big')
        pkt = makePacket(type=0x97, payload=data)
        return self.__sendPacket(pkt)

    def startBootloader(self):
        """Restart uC and load bootloader."""
        pkt = makePacket(type=0x86)
        return self.__sendPacket(pkt)

    def agc(self, status=None):
        """Get AGC status, and turn on or off."""
        data = bytearray()
        if status is not None:
            data += status.to_bytes(1, 'big')
        pkt = makePacket(type=0x98, payload=data)
        return self.__sendPacket(pkt)

    def sniffMode(self, status=None):
       """Get/set status of sniff mode."""
       data = bytearray()
       if status is not None:
           data += status.to_bytes(1,'big')
       pkt = makePacket(type=0xA1, payload=data)
       return self.__sendPacket(pkt)

    def rxGain(self, level=None):
        """Get or Set gain level of RX board (as defined by AGC)."""
        data = bytearray()
        if level is not None:
            data += level.to_bytes(1, 'big')
        pkt = makePacket(type=0x9E, payload=data)
        return self.__sendPacket(pkt)

    def rxGainRaw(self, stage=None, level=None):
        """Get or Set gain level of RX board."""
        data = bytearray()
        if stage is not None and level is not None:
            data += stage.to_bytes(1, 'big')
            data += level.to_bytes(1, 'big')
        pkt = makePacket(type=0x99, payload=data)
        return self.__sendPacket(pkt)

    def peakWinLen(self, winlen=None):
        """Get or Set window length for peak detection."""
        data = bytearray()
        if winlen is not None:
            winlen = int(winlen)
            if winlen > self.MAX_PEAKWINLEN:
                return False
            data += winlen.to_bytes(2, 'big')
        pkt = makePacket(type=0x9B, payload=data)
        return self.__sendPacket(pkt)
    
    def pktPin(self, mode=None):
        """Get or Set pkt pin mode."""
        data = bytearray()
        if mode is not None:
            data += mode.to_bytes(1, 'big')
        pkt = makePacket(type=0x89, payload=data)
        return self.__sendPacket(pkt)
    
    def transducer(self, t=None):
        """Get or Set transducer type."""
        data = bytearray()
        if t is not None:
            data += t.to_bytes(1, 'big')
        pkt = makePacket(type=0x9C, payload=data)
        return self.__sendPacket(pkt)

    def id(self, id=None):
        """Get or Set id of the modem."""
        data = bytearray()
        if id is not None:
            data = id.to_bytes(1, 'big')
        pkt = makePacket(type=0x84, payload=data)
        return self.__sendPacket(pkt)

    def testFreq(self, freqIdx=None, freqLvl=0):
        """Test freq."""
        data = bytearray()
        if freqIdx is not None:
            data  = freqIdx.to_bytes(1, 'big')
            data += freqLvl.to_bytes(1, 'big')
        pkt = makePacket(type=0xB1, payload=data)
        return self.__sendPacket(pkt)

    def testSweep(self, gc=False, gap=0):
        """Test sweep."""
        data = bytearray()
        data += gc.to_bytes(1, 'big')
        data += gap.to_bytes(1, 'big')
        pkt = makePacket(type=0xB2, payload=data)
        return self.__sendPacket(pkt)

    def testNoise(self, gc=False, step=1, dur=1):
        """Test noise."""
        data = bytearray()
        if step < 1 or dur < 1 :
            return -1
        data += gc.to_bytes(1, 'big')
        data += step.to_bytes(1, 'big')
        data += dur.to_bytes(1, 'big')
        pkt = makePacket(type=0xB3, payload=data)
        return self.__sendPacket(pkt)

    def testSound(self, dur=100):
        """Test sound (audible)."""
        data = bytearray()
        if dur < 1 or dur > 250:
            return -1
        data += dur.to_bytes(1, 'big')
        pkt = makePacket(type=0xB4, payload=data)
        return self.__sendPacket(pkt)

    def txGain(self, value=None):
        """Get or Set TX gain."""
        data = bytearray()
        if value is not None:
            data += value.to_bytes(1, 'big')
        pkt = makePacket(type=0x9A, payload=data)
        return self.__sendPacket(pkt)

    def reset(self):
        """Reset the MCU of the modem."""
        pkt = makePacket(type=0x87)
        return self.__sendPacket(pkt)
      
    def sleep(self):
        """Put MCU/modem in sleep mode."""
        pkt = makePacket(type=0x88)
        return self.__sendPacket(pkt)

    def sample(self, trigger=None, num=None, post=None):
        """Get samples of oscilloscope."""
        if trigger is None or num is None or post is None:
            return -1
        data = trigger.to_bytes(1, 'big')
        data += num.to_bytes(2, 'big')
        data += post.to_bytes(2, 'big')
        pkt = makePacket(type=0xA0, payload=data)
        return self.__sendPacket(pkt)
    
    def program(self, img='ahoi.hex', empty=False):
        # check if serially connected
        if not isinstance(self.com, ModemSerialCom):
            print("ERROR: programming only supported via serial communiation")
            return 0
        
        # check if image exists
        if not os.path.exists(img) or not os.path.isfile(img):
            print("ERROR: firmware image '%s' does not exist" % (img))
            return 0
        
        # check if stm32flash is available
        # TODO
        
        # start bootloader
        if not empty:
            if self.startBootloader():
                # TODO handle msg
                return -1
        
        # disconnect MoSh from serial
        self.com.disconnect()
        
        # install
        try:
            cmd = "stm32flash -w %s -v -R -b 115200 %s" % (img, self.com.dev)
            #params = "-w %s -v -R -b 115200 %s" % (img, self.com.dev)
            print("executing '%s'" % (cmd))
            subprocess.check_call(cmd.split())
        except OSError:
            print("ERROR: could not invoke programming tool")
            self.com.reconnect()
            return self.reset()
        except CalledProcessError:  
            print("ERROR: failed (modem might have a corrupted image and may not respond)")
            self.com.reconnect()
            return self.reset()
        
        self.com.reconnect()
        
        print("\n\nINFO: new firmware image '%s' has been installed and the device should be available\n" % (img))
        #self.getVersion()
        
        return 0

    def logOn(self, file_name=None):
        """Turn logging to file on."""
        self.com.logOn(file_name)
        #if self.logFile is not None:
        #    if not self.logFile.closed:
        #        self.logOff()
        #try:
        #    self.logFile = open(file_name, 'w', buffering=1)
        #except OSError as e:
        #    print("Failed to open {}: {}".format(file_name, str(e)))

    def logOff(self):
        """Turn logging to file off."""
        self.com.logOff()
        #if self.logFile is not None:
        #    self.logFile.flush()
        #    print("Closed logfile {}".format(self.logFile.name))
        #    self.logFile.close()
                
    def setTxEcho(self, echo):
        """Turn TX echos on/off"""
        self.echoTx = echo
        
    def setRxEcho(self, echo):
        """Turn TX echos on/off"""
        self.echoRx = echo

    def __printRxRaw(self, pkt):
        output = "RX@"
        output += "{:.3f}".format(time.time())
        output += " "
        output += packet2HexString(pkt)
        output += "("
        output += "".join(
            filter(
                lambda x: x
                in string.digits + string.ascii_letters + string.punctuation,
                pkt.payload.decode("ascii", "ignore"),
            )
        )
        output += ")"
        print("")
        print(output)

# eof
