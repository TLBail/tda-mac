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

"""Module for TCP modem com interfacing."""

#import sys
#import time

import socket

import ahoi.modem.packet
from ahoi.com.base import ModemBaseCom


class ModemSocketCom(ModemBaseCom):
  
    DFLT_PORT = 2464  # ahoi
    
    CLIENT_TIMEOUT = 1.0
    SERVER_TIMEOUT = 1.0
  
    def __init__(self, host = '', port = None, cb = None):
        """Initialize socket com."""
        # FIXME how to handle host and port?
        super().__init__('', cb)
        self.host = host
        if port is not None and int(port) > 0:
            self.port = int(port)
        else:
            self.port = ModemSocketCom.DFLT_PORT
        self.__makeDev()
        self.sock = None
        self.conn = None
        self.serverMode = False
        self.__forceClose = False
    
    
    def __del__(self):
        """Close connection."""
        self.close()
        
        
    def __makeDev(self):
        #h = self.host
        #if not h:
        #    h = 'localhost'
        self.dev = "%s:%u" % (self.host, self.port)
        
        
    def start(self, cb = None):
        """Start as server."""
        self.serverMode = True
        #self.host = '' #socket.gethostname()
        if not len(self.host):
            self.host = ModemSocketCom.__getip()
        self.__makeDev()
        if cb is not None:
            self.rxCallback = cb
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.sock.settimeout(None) # disable time-out
        self.sock.settimeout(self.SERVER_TIMEOUT)
        print("Opening server via TCP at %s:%u" % (self.host, self.port))
        #print("Opening server via TCP at %s:%u" % ('localhost', self.port))
        self.conn = None
        
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen(1)
        except Exception as e:
            print("socket.start(): " + str(e)) # FIXME debug message
            print("ERROR: cannot create server.")
            exit()
        
    
    def connect(self, cb = None):
        """Connect to server."""
        if cb is not None:
            self.rxCallback = cb
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.sock.settimeout(None) # disable time-out
        # FIXME do we need a time-out here?
        # having it leads to a 103 exception (software abort),
        # in interleaving fashion with expected 111 (conn refused)
        #self.sock.settimeout(self.CLIENT_TIMEOUT)

        print("Connecting via TCP to %s:%u" % (self.host, self.port))
        while True:
            try:
                self.sock.connect((self.host, self.port))
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self.conn = self.sock
                break
            except Exception as e:
                print("socket.connect(): " + str(e)) # FIXME debug message
                choice = input("Server not available. Retry? [Y/n] ")
                if choice.lower() in ["n", "no"]:
                    exit()


    def close(self):
        """Terminate."""
        if self.sock:
            self.__forceClose = True
            if self.sock != self.conn and self.conn:
                try:
                    self.conn.shutdown(socket.SHUT_RDWR)
                    self.conn.close()
                except Exception as e:
                    print("socket.close() conn: " + str(e)) # FIXME debug message
                    pass
                self.conn = None
            
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            except Exception as e:
                print("socket.close() sock: " + str(e)) # FIXME debug message
                pass
            self.sock = None
            self.__forceClose = False
        
        super().close()

        
    def receive(self):
        """Receive and decode TCP packet"""
        
        while not self.__forceClose:
            if self.serverMode:
                while not self.__forceClose:
                    try:
                        self.conn, addr = self.sock.accept()
                        self.conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        #self.sock.settimeout(self.SERVER_TIMEOUT)
                        # make sure that receiving doesn't block forever
                        self.conn.settimeout(self.SERVER_TIMEOUT)
                        print("Connection from %s:%u established" % (addr[0], addr[1]))
                        break
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print("socket.receive() srv: " + str(e)) # FIXME debug message
                        return
            
            while self.conn and not self.__forceClose:
                try:
                    #rx = self.conn.recv(1, socket.MSG_CMSG_CLOEXEC)
                    rx = self.conn.recv(1)
                    if not rx:
                        if not self.serverMode:
                            print("ERROR: socket probably disconnected")
                            return # FIXME is this enough?
                        else:
                            print("Client disconnected")
                            break
                except socket.timeout:
                    continue
                except Exception as e:
                    print("socket.receive() rx: " + str(e)) # FIXME debug message
                    return
                
                super().processRx(rx)
        
        return
      
      
    def send(self, pkt):
        """Send a packet."""
        
        # send encoded data
        tx = super().processTx(pkt)
        self.conn.sendall(tx)
        
        
    def scanAndSelect():
        # TODO any better solution possible?
        return ModemBaseCom.scanAndSelect(ModemSocketCom)
    

    def scan(subrange = range(1,255), port = None, timeout = 0.1):
        baseIp = ModemSocketCom.__getip()
        baseIpParts = baseIp.split('.')
        ipLst = []
        if len(baseIpParts) != 4:
            return
        
        if port is None:
            port = ModemSocketCom.DFLT_PORT
        
        baseIpParts[3] = str(subrange[0])
        sip = '.'.join(baseIpParts)
        baseIpParts[3] = str(subrange[-1])
        eip = '.'.join(baseIpParts)
        print("probing network %s - %s on port %u" % (sip, eip, port))
        i = 0
        for p in subrange:
            if i % 64 == 0:
                print('%3u: ' % (subrange[i]), end='', flush=True)
            
            # prepare ip address to test
            baseIpParts[3] = str(p)
            tip = '.'.join(baseIpParts)            
            #print("%s " % tip, end='')
            
            # try to connect and add to list, if successful
            try:
                tsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tsock.settimeout(timeout) # disable time-out
                tsock.connect((tip, port))
                tsock.close()
                ipLst.append(tip)
                print('*', end='', flush=True)
            except:
                print('.', end='', flush=True)
            
            # line-wrap
            i = i + 1
            if i % 64 == 0 or i == len(subrange)  :
                print('', flush=True)
                
        return ipLst


    def __getip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
# eof
