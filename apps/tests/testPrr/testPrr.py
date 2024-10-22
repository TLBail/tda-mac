#! /usr/bin/env python3

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

"""test script to assess PRR of modems"""
import time
import configparser
import os
import time
import sys
import string

# modem and serial connection
from ahoi.modem.modem import Modem

# from packet import getBytes
from ahoi.modem.packet import getHeaderBytes
from ahoi.modem.packet import getFooterBytes


#def startTest(modem, role, src, pktcount, payload, s0, s1, sleepTime, pktType, txGain, distance, spread):
def startTest(modem, role, pktcount, payload, rxg, sleepTime, pktType, txGain, spread):
    """Start a single test."""
    #filename = "{}_".format(time.strftime("%d%m%Y-%H%M%S"))
    
    # prepare file name
    filename = ""
    #filename += "id{:03d}_".format(src)
    filename += "{}_".format(role)
    filename += "pkt-{:04d}_".format(pktcount)
    filename += "pay-{:03d}_".format(payload)
    if rxg is None:
        filename += "rxg-ac_"
    else:
        filename += "rxg-{:02d}_".format(rxg)
    filename += "txg-{:02d}_".format(txGain)
    filename += "fs-{:1d}".format(spread)
    filename += ".{}".format(time.strftime("%Y%m%d-%H%M%S"))
    filename += ".log"
    
    # set up modem
    modem.logOn(file_name=filename)
    modem.id()
    modem.getVersion()
    modem.getConfig()
    modem.bitSpread(spread)
    #modem.rangeDelay()
    modem.txGain(txGain)
    if rxg is None:
        modem.agc(1)
        modem.rxGain()
    else:
        modem.agc(0)
        modem.rxGain(rxg)
    modem.clearPacketStat()
    modem.clearSyncStat()
    modem.clearSfdStat()
    # more stats
    modem.getPowerLevel()
    modem.rxThresh()
    modem.rxLevel()
    
    # run experiment after user OK
    if role == "tx":
        input("RX ready?")
        for i in range(0, pktcount):
            data = bytes(os.urandom(payload))
            modem.send(src=0x00, dst=0xFF, payload=data, status=0, dsn= (i % 256), type=pktType)
            time.sleep(sleepTime)
        print("TX DONE!")
    else:
        input("TX done?")
        
    # stats
    modem.getPacketStat()
    modem.getSyncStat()
    modem.getSfdStat()
    modem.getPowerLevel()
    
    # finalize
    time.sleep(1)
    modem.logOff()


def main():
    """Main."""
    
    ##
    # process command lines arguments
    ##
    import argparse
    parser = argparse.ArgumentParser(
        description="AHOI test toolbox - PRR test.",
        epilog="""\
          NOTE: no security measures are implemented.
          Input is not validated.""")


    parser.add_argument(
        '-c', '--config',
        type = str,
        default = 'config/default.ini',
        dest = 'confFile',
        help = 'path to config file (default: config/default.ini)'
        )
    
    parser.add_argument(
        '-d', '--device',
        type = str,
        default = None,
        dest = 'dev',
        help = 'device with modem connection (default: None)'
        )

    args = parser.parse_args()

    # create modem instance
    myModem = Modem()
    myModem.connect(args.dev)
    myModem.setTxEcho(True)
    myModem.setRxEcho(True)
    #myModem.addRxCallback(printRxRaw)
    myModem.receive(thread = True)

    # open config
    testConfig = configparser.ConfigParser()
    testConfig.read(args.confFile)
    
    # read config
    #role = testConfig['PARAMETERS'].getboolean('role')
    #if not role in ["tx", "rx"]:
    #    print("Ups, role '{}' is invalid. Aborting.".format(role))
    #    sys.exit(1)
    while True:
        role = input("Are you rx or tx:")
        if role in ["tx", "rx"]:
            print("Ok. You are {}.".format(role))
            break

    testAgc    = testConfig['PARAMETERS'].getboolean('testAgc')
    pktCount   = testConfig['PARAMETERS'].getint('pktCount')
    pktType    = int(testConfig['PARAMETERS']['pktType'], 16)
    sleepTime  = testConfig['PARAMETERS'].getfloat('sleepTime')
    payloadLen = list(map(int, testConfig['PARAMETERS']['payloadLength']
                         .split(',')))
    #filterS0   = testConfig['PARAMETERS']['filterS0'].split(',')
    rxGain     = list(map(int, testConfig['PARAMETERS']['rxGain'].split(',')))
    txGain     = list(map(int, testConfig['PARAMETERS']['txGain'].split(',')))
    bitSpread  = list(map(int, testConfig['PARAMETERS']['bitSpread'].split(',')))
    
    #
    testIdx = 0
    for sp in bitSpread:
        for pl in payloadLen:
            for tx in txGain:
                if testAgc:
                    doTest = input("Do test #{} (pkts={},pay={},AGC,txgain={},spread={})? [Y/n/exit]"
                                   .format(testIdx, pktCount, pl, tx, sp))
                    if doTest.lower() == "exit":
                        myModem.close()
                        return
                    if doTest.lower() in ["n", "no", "nein"]:
                        print("Skip test #{}.".format(testIdx))
                    else:
                        startTest(modem=myModem, role=role,
                                  pktcount=pktCount, payload=pl, rxg=None, sleepTime=sleepTime, pktType=pktType, txGain=tx, spread=sp)
                    testIdx = testIdx + 1
                for rxg in rxGain:
                    if rxg >= 0:
                        doTest = input("Do test #{} (pkts={},pay={},rxgain={},txgain={},spread={})? [Y/n/exit]"
                                      .format(testIdx, pktCount, pl, rxg, tx, sp))
                        if doTest.lower() == "exit":
                            myModem.close()
                            return
                        if doTest.lower() in ["n", "no", "nein"]:
                            print("Skip test #{}.".format(testIdx))
                        else:
                            startTest(modem=myModem, role=role,
                                      pktcount=pktCount, payload=pl, rxg=rxg, sleepTime=sleepTime, pktType=pktType, txGain=tx, spread=sp)
                        testIdx = testIdx + 1

    myModem.close()


if __name__ == "__main__":
    main()
