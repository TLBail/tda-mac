#! /usr/bin/env python3

#
# Copyright 2016-2021
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

"""This is Modem Shell (mosh)."""

import time
import sys
import signal
import re
import time
import threading
import os
import argparse

try:
    import readline
except ImportError:
    print("No readline found. Arrow keys likely won't work.")

# modem and serial connection
from ahoi.modem.modem import Modem

# from packet import getBytes
from ahoi.modem.packet import getHeaderBytes
from ahoi.modem.packet import getFooterBytes

# handlers
# from ahoi.handlers.SamplePlotHandler import SamplePlotHandler
# from ahoi.handlers.RangingHandler import RangingHandler


##
# CTRL-C handler
##
sigIntEn = True
gIrq = False
def sigInt_handler(signal, frame):
    """Handle SIGINT (Ctrl+C)."""
    if sigIntEn:
        pass
        # FIXME this currently hangs due to input(...) in input thread
        #print('Received SIGINT, closing ...')
        #myModem.close()
        #print("done, bye, bye.")
        #exit()
    
    else:
        global gIrq
        gIrq = True
        #sigIntEn = True
        

def sigInt_enable():
    global sigIntEn, gIrq
    sigIntEn = True
    gIrq = False


def sigInt_disable():
    global sigIntEn, gIrq
    sigIntEn = False
    gIrq = False


def sigInt_check():
    global gIrq
    if gIrq:
        sigInt_enable()
        return True
    return False


##
# setup commands
##
cmdList = {
    "allstat": {
        'func': "doAllStat",
        'param': '',
        'info': "Get all statistics (this is equivalent to calling all '...stat' commands subsequently)"
    },
    "allstatclear": {
        'func': "doAllStatClear",
        'param': '',
        'info': "Clear all statistics (this is equivalent to calling all '...statclear' commands subsequently)"
    },
    "version": {
        'func': "doVersion",
        'param': '',
        'info': "Get firmware version"
    },
    "config": {
        'func': "doConfig",
        'param': '',
        'info': "Get build configuration of the firmware"
    },
    #"freqbandsnum": {
    #    'func': "doFreqBandsNum",
    #    'param': '[num:int]'
    #},
    #"freqbands": {
    #    'func': "doFreqBands",
    #    'param': '[FREQ_BAND_NUM_MAX]x[FREQ_CARRIER_NUM_MAX]'
    #},  # TODO
    #"freqcarriersnum": {
    #    'func': "doFreqCarriersNum",
    #    'param': '[num:int]'
    #},
    #"freqcarriers": {
    #    'func': "doFreqCarriers",
    #    'param': '[FREQ_BAND_NUM_MAX]x[FREQ_CARRIER_NUM_MAX]'
    #},  # TODO
    "rxthresh": {
        'func': "doRxThresh",
        'param': '[thresh:int]',
        'info': "Get/Set receive threshold (in percent). Changing this value should be done in conjunction with the result of calling 'rxlevel' several times. As a rule of thumb, the threshold should be 2-4 times the maximum rxlevel output."
    },  # --> syncThresh
    "rxlevel": {
        'func': "doRxLevel",
        'param': '',
        'info': "Get current amplitudes (levels) of the sync frequencies."
    },   # --> syncLevel
    "spreadcode": {
        'func': "doBitSpread",
        'param': 'length:int',
        'info': "DEPRECATED\nThis command has been superseded by 'bitspread' and will be removed in a later version of pylib."
    },
    "bitspread": {
        'func': "doBitSpread",
        'param': 'chips:int',
        'info': "Get/set number of chips (spreading factor) per symbol."
    },
    "filterraw": {
        'func': "doFilterRaw",
        'param': '[stage:int value:int]',
        'info': "TESTING\nGet/set raw values for filter stages"
    },
    "synclen": {
        'func': "doSyncLen",
        'param': '[txlen:int rxlen:int]',
        'info': 'Get/set number of sync symbols being sent (txlen) and used for synchronization (rxlen <= txlen)'
    },
    "sniffmode": {
        'func': "doSniffMode",
        'param': 'en:(on/off)',
        'info': "Enable/disable sniffing mode, in which the modem will stop sending any ACKs (regular and ranging)"
    },
    "agc": {
        'func': "doAgc",
        'param': 'en:(on/off)',
        'info': "Get/set state of Automatic Gain Control (AGC). Note that enabling AGC will overwrite a previously set receive gain."
    },
    "rxgain": {
        'func': "doRxGain",
        'param': 'level:int',
        'info': "Get/set receive gain level (0-18, steps of 2dB, 0 being lowest). Changing the gain level has no (persisting) effect, if AGC is enabled."
    },
    "rxgainraw": {
        'func': "doRxGainRaw",
        'param': 'stage:int level:int',
        'info': "Get/set receive gain of the two individual stages (0,1). Changing the gain level has no (persisting) effect, if AGC is enabled."
    },
    "powerlevel": {
        'func': "doPowerLevel",
        'param': '',
        'info': "Get current power level on the channel (in percent). Measurement duration is that of a single symbol. A value above 100%% indicates potential oversteer."
    },
    "packetstat": {
        'func': "doPacketStat",
        'param': '',
        'info': "Get packet statistics since last reset"
    },
    "packetstatclear": {
        'func': "doPacketStatClear",
        'param': '',
        'info': "Clear packet statistics"
    },
    "peakwinlen": {
        'func': "doPeakWinLen",
        'param': '[winlen:float(ms)]',
        'info': "TESTING\nGet/set length of window to find frequency peaks/symbols"
    },
    "pktpin": {
        'func': "doPktPin",
        'param': '[mode:int]',
        'info': "Set mode of pkt pin (0 = disabled, 1 = queue state, 2 = ranging)"
    },
    "range": {
        'func': "doRange",
        'param': 'rep:int intvl:float(sec) [addr:int [data:string]]',
        'info': "Send 'rep' ranging requests every 'intvl' seconds as broadcast. Broadcast requests will be answered by all receiving modems with a response. If the optional parameter 'addr' is provided, the request will be addressed to that modem (which will be the only one sending a response). Any response will be delayed as configured with 'range-delay'. Optional 'data' may be added to the request."
    },
    "range-delay": {
        'func': "doRangeDelay",
        'param': 'delay:float(ms)',
        'info': "get/set the delay of the modem before answering a broadcast range request"
    },
    "reset": {
        'func': "doReset",
        'param': '',
        'info': "reset the modem (clearing all non-persistent state information)"
        },
    "sample": {
        'func': "doSample",
        'param': 'trig:int len:int post:int',
        'info': "obtain len samples from the channel (as seen by the modem) with post samples taken after the trigger point and len-post before it (0 < len,post <= 20000). Triggers are:\n0: clear, 1: now, 2: sync, 3: end of packet"
    },
    "send": {
        'func': "doSend",
        'param': 'addr:int pkttype:hex [flags:int [data:string]]'
    },
    "sendrep": {
        'func': "doSendRep",
        'param': 'rep:int delay:float(sec) addr:int pkttype:hex [flags:int [data:string]]'
    },
    "sfdstat": {
        'func': "doSfdStat",
        'param': ''
    },
    "sfdstatclear": {
        'func': "doSfdStatClear",
        'param': ''
    },
    "sleep": {
        'func': "doSleep",
        'param': '',
        'info': "put modem into sleep mode (can only be undone via powercycle or WAKEUP pin)"
    },
    "syncstat": {
        'func': "doSyncStat",
        'param': ''
    },
    "syncstatclear": {
        'func': "doSyncStatClear",
        'param': ''
    },
    "transducer": {
        'func': "doTransducer",
        'param': '[transducer:uint(TRANSDUCER_*)]',
        'info': "get/set transducer to compensate its specific transfer function."
    },
    "txgain": {
        'func': "doTxGain",
        'param': 'value:int',
        'info': "get/set transmit gain (in steps of -3dB, where value is a (positive) step number and 0 is maximum gain/output)"
    },
    "id": {
        'func': "doId",
        'param': '[id:int]',
        'info': "get/set modem id"
    },
    "testfreq": {
        'func': "doTestFreq",
        'param': '[index:int [lvl:int]]'
    },
    "testsweep": {
        'func': "doTestSweep",
        'param': '[gaincomp:bool<false> gap:uint<0>)]'
    },
    "testnoise": {
        'func': "doTestNoise",
        'param': '[gaincomp:bool<false> step:uint<1> duration:uint<1>]'
    },
    "testsound": {
        'func': "doTestSound",
        'param': '[duration:uint<100>]',
        'info': "Play an audible test sound (ca. 4kHz) for duration/100 s"
    },
    "batvol": {
        'func': "doBatVol",
        'param': '',
        'info': "Read battery voltage from modem (mV)"
    },
    "bootloader": {
        'func': "doBootloader",
        'param': '',
        'info': "Reset modem and boot into bootloader mode (needs hardware reset to resume normal operation)"
    },
    "program": {
        'func': "doProgram",
        'param': 'hex-image:string [empty:bool<false>]',
        'info': "EXPERIMENTAL\nflash a new modem firmware image to an AHOI modem. If the device has not been programmed before, you must put it in bootloader mode manually (push boot button and power cycle the device) and call this command with parameter empty set to 'true'."
    },
}


def doSniffMode(inp):
    """Get/set sniff mode status."""
    sniff = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
        if param[0] == 'on' or param[0].lower() == 'true':
            sniff = 1
        elif param[0] == 'off' or param[0].lower() == 'false':
            sniff = 0
        else:
            return -1
    return myModem.sniffMode(sniff)


def doAgc(inp):
    """Get/Set AGC status."""
    agc_status = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
        if param[0] == 'on' or param[0].lower() == 'true':
            agc_status = 1
        elif param[0] == 'off' or param[0].lower() == 'false':
            agc_status = 0
        else:
            return -1

    return myModem.agc(agc_status)


def doBatVol(inp):
    """Get Battery Voltage."""
    return myModem.getBatVoltage()


def doBootloader(inp):
    """Reset uC and start Bootloader."""
    return myModem.startBootloader()


def doProgram(inp):
    """Reset uC, start Bootloader, write firmware image (hex)."""
    if len(inp) < 2:
        return -1
      
    param = inp[1].split()
    empty = False
    if len(param) > 2:
        return -1
    elif len(param) == 2:
        if param[1].lower() == 'true':
            empty = True
    
    return myModem.program(param[0], empty)
    

def doDistance(inp):
    """Get stored distance."""
    id = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
        id = int(param[0])
    return myModem.getDistanceTo(id)


def doRxGain(inp):
    """Get/Set rx gain level."""
    level = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1

        level = int(param[0])
    return myModem.rxGain(level)


def doRxGainRaw(inp):
    """Get/Set rx gain level."""
    stage = None
    level = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 2:
            return -1

        stage = int(param[0])
        level = int(param[1])
    return myModem.rxGainRaw(stage, level)


def doPeakWinLen(inp):
    """Get/set peak window length."""
    winlen = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
        winlen = int(float(param[0]) * 1000)
    return myModem.peakWinLen(winlen)


def doPktPin(inp):
    """Get/Set rx gain level."""
    mode = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1

        mode = int(param[0])
    return myModem.pktPin(mode)


def doTransducer(inp):
    """Get/set transducer type."""
    t = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
        t = int(param[0])
    return myModem.transducer(t)


def doConfig(inp):
    """Get modem config."""
    return myModem.getConfig()


def doFilterRaw(inp):
    """Get/Set rx gain."""
    stage = None
    level = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 2:
            return -1

        stage = int(param[0])
        level = param[1]
    return myModem.filterRaw(stage, level)


def doFreqBands(inp):
    """Get/Set freq band setup."""
    print("WARNING: setter not implemented")
    # howto = 'USAGE: TODO'

    # if len(inp) > 1:
    #    param = inp[1].split(' ')
    #    if len(param) != 4:
    #      return -1

    #    data = bytearray()
    #    for i in range(4):
    #        data += int(param[i]).to_bytes(1, 'big')

    return myModem.freqBands()


def doFreqBandsNum(inp):
    """Get/Set freq bands num."""
    num = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1

        num = int(param[0])

    return myModem.freqBandsNum(num)


def doFreqCarriers(inp):
    """Get/Set freq carrier setup."""
    print("WARNING: setter not implemented")
    # howto = 'USAGE: TODO'

    # if len(inp) > 1:
    #    param = inp[1].split(' ')
    #    if len(param) != 4:
    #        #return -1
    #
    #    data = bytearray()
    #    for i in range(4):
    #        data += int(param[i]).to_bytes(1, 'big')

    return myModem.freqCarriers()


def doFreqCarriersNum(inp):
    """Get/Set freq carrier num."""
    num = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1

        num = int(param[0])
    return myModem.freqCarrierNum(num)


def doId(inp):
    """Get/Set modem id."""
    modem_id = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
        modem_id = int(param[0])
    return myModem.id(modem_id)


def doLogOpen(inp):
    """Open Log file."""
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
    return myModem.logOn(param[0])


def doLogClose():
    """Close log file."""
    myModem.logOff()
    return 0


def doPacketStat(inp):
    """Get packet stats."""
    return myModem.getPacketStat()


def doPacketStatClear(inp):
    """Clear packet stat."""
    return myModem.clearPacketStat()


def doSyncStat(inp):
    """Get sync stats."""
    return myModem.getSyncStat()


def doSyncStatClear(inp):
    """Clear sync stat."""
    return myModem.clearSyncStat()

def doSfdStat(inp):
    """Get sfd stats."""
    return myModem.getSfdStat()


def doSfdStatClear(inp):
    """Clear sfd stat."""
    return myModem.clearSfdStat()

def doAllStat(inp):
    """Get al tx/rx stats."""
    myModem.getPacketStat()
    myModem.getSyncStat()
    myModem.getSfdStat()
    return 0

def doAllStatClear(inp):
    """Clear all tx/rx stat."""
    myModem.clearPacketStat()
    myModem.clearSyncStat()
    myModem.clearSfdStat()
    return 0

def doPause(inp):
    """Do nothing for a while."""
    if len(inp) != 2:
        return -1

    param = inp[1].split(' ')
    if len(param) != 1:
        return -1

    delay = float(param[0])
    print("sleeping %g seconds ..." % delay)
    time.sleep(delay)

    return 0
 

# TODO  
#def doPlots(inp):
#    """Enable/disable plots."""
#    if len(inp) > 1:
#        param = inp[1].split(' ')
#        if len(param) != 1:
#            return -1
#        if (param[0] == 'on'):
#            # register plot handlers
#            #myModem.addRxHandler(SamplePlotHandler())
#            #myModem.addRxHandler(RangingHandler())
#            pass
#        elif (param[0] == 'off'):
#            # deregister plot handlers
#           # myModem.addRxHandler(SamplePlotHandler())
#            #myModem.addRxHandler(RangingHandler())
#            pass
#        else:
#            return -1
#
#    return 0


def doPowerLevel(inp):
    """Get power level."""
    return myModem.getPowerLevel()


##
# run commands from file (batch mode)
##
runFile = False
runFileName = ''


def doRun(inp):
    """Run script from file."""
    global runFile, runFileName

    if len(inp) != 2:
        return -1

    param = inp[1].split(' ')
    if len(param) != 1:
        return -1

    runFileName = param[0]
    if (os.path.isfile(runFileName)):
        runFile = open(runFileName, 'r')
        print("running commands from \"%s\"" % runFileName)
        return 0

    else:
        print("file \"%s\" does not exist" % runFileName)
        return 1


def doRxLevel(inp):
    """Get Rx threshold level."""
    return myModem.rxLevel()


def doRxThresh(inp):
    """Set up rx threshold."""
    thresh = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1

        thresh = int(param[0])
    return myModem.rxThresh(thresh)


def doRange(inp):
    """Get distance to other modems."""
    if (len(inp) < 2):
        return -1

    # rep / delay
    param = inp[1].split(' ')
    if (len(param) < 2):
        return -1

    rep = int(param[0])
    delay = float(param[1])
    dst = 255
    if (len(param) > 2 and param[2] != '*'):
        dst = int(param[2])
    data = bytearray()
    if (len(param) > 3):
        data = param[3].encode('ascii')

    # send rep times with delay
    sigInt_disable()
    for i in range(0, rep):
        if sigInt_check():
            return 0
        
        if i > 0:
            time.sleep(delay)

        # send ping and request pong (ranging ack)
        ret = myModem.send(type=0x52, dst=dst, src=0, dsn=(i%256), status=2, payload=data)
        if ret != 0:
            return -1

    sigInt_enable()

    return 0


def doRangeDelay(inp):
    """Set delay for range answer."""
    delay = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if(len(param) != 1):
            return -1
        delay = int(param[0])
    return myModem.rangeDelay(delay)


def doReset(inp):
    """Reset the modem."""
    return myModem.reset()


def doSleep(inp):
    """Sleep the modem."""
    return myModem.sleep()


def doSample(inp):
    """Get samples."""
    if (len(inp) < 2):
        return -1

    param = inp[1].split(' ')
    if (len(param) < 3):
        return -1

    trig = int(param[0])
    num = int(param[1])
    post = int(param[2])
    return myModem.sample(trig, num, post)


def doSend(inp):
    """Send a packet."""
    if(len(inp) != 2):
        return -1

    # send pkttype data
    param = inp[1].split(' ')
    if (len(param) < 2):
        return -1
    # dst = MM_ADDR_BCAST
    dst = None
    if (param[0] != '*'):
        if not param[0].isdigit():
            return -1
        dst = int(param[0])
    try:
        pkttype = int(param[1], 16)
        if (pkttype >= 0x80):
            return -1
    except ValueError:
        return -1
    
    status = 0
    if(len(param) > 2):
        try:
            status = int(param[2])
        except ValueError:
            status = 0

    data = ''
    if len(param) > 3:
        data = data.join(param[3:])

    return myModem.send(src=0, dst=dst, type=pkttype, status=status,
                        payload=data.encode('ascii', 'ignore'))


def doSendRep(inp):
    """Send multiple packets (including sequence number)."""
    if (len(inp) < 2):
        return -1

    # send pkttype data
    param = inp[1].split(' ')
    if (len(param) < 4) or (len(param) > 6):
        return -1

    # init
    try:
        rep = int(param[0])
        delay = float(param[1])
    except ValueError:
        return -1

    if (param[2] != '*'):
        if not param[2].isdigit():
            return -1
        dst = int(param[2])
    try:
        pkttype = int(param[3], 16)
        if (pkttype >= 0x80):
            return -1
    except ValueError:
        return -1
    
    status = 0
    if(len(param) > 4):
        try:
            status = int(param[4])
        except ValueError:
            status = 0
    
    data = ''
    if len(param) == 6:
        data = param[5]

    # send rep times with delay
    sigInt_disable()
    for i in range(0, rep):
        if sigInt_check():
            return 0
        
        if i > 0:
            time.sleep(delay)

        print("send-rep packet %3u of %u" % (i+1, rep))
        ret = myModem.send(src=0, dst=dst, type=pkttype, status=status, dsn=(i%256),
                           payload=data.encode('ascii', 'ignore'))
        if ret != 0:
            return -1

    sigInt_enable()

    return 0


def doBitSpread(inp):
    """Set up spread-code."""
    chips = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1

        chips = int(param[0])
    return myModem.bitSpread(chips)


def doSyncLen(inp):
    """Get/Set sync/preamble length."""
    txlen = None
    rxlen = None
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) != 2:
            return -1

        txlen = int(param[0])
        rxlen = int(param[1])

    return myModem.syncLen(txlen, rxlen)


def doTestFreq(inp):
    """Test single frequency."""
    freq_idx = None
    freq_lvl = 0
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) < 1 or len(param) > 2 :
            return -1
        freq_idx = int(param[0])
        if (len(param) == 2) :
          freq_lvl = min(int(param[1]), 100)

    return myModem.testFreq(freq_idx, freq_lvl)


def doTestSweep(inp):
    """Test frequency sweep."""
    gc  = False
    gap = 0
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) < 0 or len(param) > 2 :
            return -1

        gc = param[0].lower() == 'true' #or isint(param[0]) != 0
        if len(param) > 1 :
            gap = int(param[1])

    return myModem.testSweep(gc, gap)


def doTestNoise(inp):
    """Test noise (white noise in comm band) output."""
    gc   = False
    step = 1
    dur  = 1
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) < 0 or len(param) > 3 :
            return -1

        gc = param[0].lower() == 'true' #or int(param[0]) != 0
        if len(param) > 1 :
            gap = int(param[1])
        if len(param) > 2 :
            dur = int(param[2])

    return myModem.testNoise(gc, step, dur)


def doTestSound(inp):
    """Test sound (audible) output."""
    dur  = 100
    if len(inp) > 1:
        param = inp[1].split(' ')
        if len(param) < 0 or len(param) > 1 :
            return -1

        dur = int(param[0])

    return myModem.testSound(dur)


def doTxGain(inp):
    """Get/set Tx gain."""
    value = None
    if (len(inp) > 1):
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1

        value = int(param[0])

    return myModem.txGain(value)


def doWaitKey(inp):
    """Wait for input."""
    if len(inp) > 2:
        return -1

    match = ''
    if len(inp) == 2:
        param = inp[1].split(' ')
        if len(param) != 1:
            return -1
        match = param[0]

    if match == '':
        prompt = '\nwaiting - hit enter to continue ... '
    else:
        prompt = '\nwaiting - enter "%s" to continue ... ' % (match)
    while True:
        inp = input(prompt)
        if match == '' or match == inp:
            break

    return 0


def doVersion(inp):
    """Get/set modem id."""
    return myModem.getVersion()


def readInput():
    """Read input from console."""
    global runFile
    global prompted

    if (runFile):
        inp = runFile.readline()

        if (len(inp) > 0):
            inp = inp.rstrip('\n')
            print('\nmosh@%s >> %s (from "%s")' % (dev, inp, runFileName))
        else:
            runFile.close()
            runFile = False

    if (not runFile):
        prompted = True
        inp = input("\nmosh@%s >> " % (dev))
        prompted = False

    return inp



def printUsage(cmd):
    """Print usage of mosh."""
    if cmd in cmdList:
        print("\nUSAGE: %s %s" % (cmd, cmdList[cmd]['param']))
        if 'info' in cmdList[cmd]:
            print("\nINFO:  " + cmdList[cmd]['info'])
    else:
        print("\nERROR: no help available for unknown command")
    return

    
  

def __inputThread():

    while True:
        # get keyboard input (blocking)

        # TODO read from file if provided via run command

        inp = readInput()

        # split input into command and params
        inp = inp.strip()  # strip leading/trailing spaces
        inp = re.sub("\\s{2,}", " ", inp)  # remove multiple spaces (make one)
        inp = inp.split(' ', 1)
        cmd = inp[0]

        if (len(cmd) > 0 and cmd[0] != '#'):
            if cmd == 'exit' or cmd == 'quit':
                myModem.close()
                exit()

            elif cmd == 'help' or cmd == '?':
                if len(inp) == 1:
                    print("\navailable commands:\n")
                    for c in sorted(cmdList):
                        print("  " + c)
                elif len(inp) == 2:
                    printUsage(inp[1])
                else:
                    print("ERROR: invalid call of \"help\"")

            elif cmd == 'logon':
                doLogOpen(inp)

            elif cmd == 'logoff':
                doLogClose()

            elif cmd == 'run':
                doRun(inp)

            elif cmd == 'pause':
                doPause(inp)

            elif cmd == 'waitkey':
                doWaitKey(inp)
                
            #elif cmd == 'plots':
            #    doPlots(inp)

            else:
                if cmd in cmdList:
                    try:
                        ret = eval(cmdList[cmd]['func'])(inp)
                    except ValueError:
                        # not the best error handling but better than what we had before
                        # (at least no crash)
                        print("ERROR: Could not parse one of the parameters")

                    if ret != 0:
                        print("ERROR: improper parameter list!")
                        printUsage(inp[0])

                    if runFile:
                        # HACK sleep shortly to wait for reply
                        # before executing next command
                        time.sleep(0.1)
                    else:
                        # HACK sleep shortly to show rx
                        # after rx without new prompt
                        time.sleep(0.01)
                else:
                    print("ERROR: unknown command ")




if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigInt_handler)
    # print('Press Ctrl+C')
    # signal.pause()

    ##
    # process command lines arguments
    ##
    
    parser = argparse.ArgumentParser(
        description="AHOI Modem Shell (MoSh).",
        epilog="""\
          NOTE: no security measures are implemented.
          Input is not validated.""")
    
    parser.add_argument(
        nargs = '?',
        type = str,
        default = None,
        dest = 'dev',
        metavar = 'device',
        help = 'device name with connected ahoi modem')
    
    args = parser.parse_args()

    # create modem instance and connect
    myModem = Modem()
    myModem.connect(args.dev)
    dev = myModem.com.dev
    myModem.setTxEcho(True)
    myModem.setRxEcho(True)
    #myModem.addRxCallback(printRxRaw)
    
    # sample plot handler
    #myModem.addRxHandler(SamplePlotHandler())
    #myModem.addRxHandler(RangingHandler())
    
    # create input thread
    print("\nEnter your commands below.\r\n"
        "Type \"help\" for a list of commands, type \"exit\" to leave"
    )
    inputThread = threading.Thread(target=__inputThread)
    inputThread.start()
    
    # process
    myModem.receive()
    
    # finish up
    inputThread.join()
    
# eof
