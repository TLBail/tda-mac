#! /usr/bin/env python3

#
# Copyright 2019-2020
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

"""This is the ahoi serial forwarder (TCP to serial translator)."""

#import signal
import time
import sys
import threading
import signal
import argparse

from ahoi.com.serial import ModemSerialCom
from ahoi.com.socket import ModemSocketCom


sock = None
com = None
sockThread = None


def sigInt_handler(signal, frame):
    # finish up
    print('Received SIGINT, closing ...')
    if sock is not None:
        sock.close()
    if com is not None:
        com.close()
    if sockThread is not None:
        sockThread.join()
    exit()
  

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigInt_handler)
    
    ##
    # process command lines arguments
    ##
        
    parser = argparse.ArgumentParser(
        description="AHOI serial forwarder.",
        epilog="""\
          NOTE: no security measures are implemented.
          Input is not validated.""")
    
    parser.add_argument(
        '-i', '--ip',
        type = str,
        default = '',
        dest = 'ip',
        help = 'TCP host (IP) address'
        )

    parser.add_argument(
        '-p', '--port',
        type = int,
        default = None,
        dest = 'port',
        help = 'TCP port (default: '+str(ModemSocketCom.DFLT_PORT)+')'
        )
    
    parser.add_argument(
        nargs = '?',
        type = str,
        default = None,
        dest = 'dev',
        metavar = 'device',
        help = 'device name with connected ahoi modem')
    
    args = parser.parse_args()

    # setup serial connection
    if args.dev is None:
        args.dev = ModemSerialCom.scanAndSelect()
        
    com = ModemSerialCom(args.dev)
    
    # setup tcp connection
    sock = ModemSocketCom(port = args.port, host = args.ip)

    # cross connect
    com.connect(sock.send)
    sock.start(com.send)
    
    # logging
    t = time.strftime("%Y%m%d-%H%M%S")
    com.logOn("sfwd-"+t+".tcp.log")
    sock.logOn("sfwd-"+t+".serial.log")

    # create input thread
    sockThread = threading.Thread(target = sock.receive)
    sockThread.start()
    
    # serial receive (blocking)
    com.receive()

    # finish up
    sockThread.join()

    sock.close()
    com.close()

# eof
