#
# Copyright 2018-2020
# 
# Fabian Steinmetz, Bernd-Christian Renner, and
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

import time
import configparser
import os
import sys
import string
import threading
import math

from dataclasses import dataclass
from PIL import Image
from io import BytesIO

# modem imports
from ahoi.modem.modem import Modem
from ahoi.modem.packet import getHeaderBytes
from ahoi.modem.packet import getFooterBytes

# other imports
from ahoi.imgtx.helpers import imageviewer
from ahoi.imgtx.helpers import camera
from ahoi.imgtx.helpers import jfif_splitter

SIMULATION = False # simulation mode with bridged FTDI connectors. Soft-Ack required!


# Packet Types
TYPE_CMD = 0x7A
TYPE_DATA = 0x7B
TYPE_SOFT_ACK = 0x7C
TYPE_HARD_ACK = 0x7F # has to match with the firmware

# CMD Packets
CMD_CAP   = 0x00
CMD_BEGIN = 0x01
CMD_END   = 0x02

# IDX General
IDX_TYPE = 0
MAX_CMD_LENGTH = 10
# IDX CAP
IDX_SIZE_X = slice(1,2+1)
IDX_SIZE_Y = slice(3,4+1)
IDX_QUAL = 5
IDX_FLASH  = 6
# IDX BEGIN
IDX_NUM_HEAD = slice(1,2+1)
IDX_NUM_DATA = slice(3,4+1)
# IDX END
IDX_NUM_RX_PKT  = slice(1,2+1)
IDX_NUM_RX_ACK  = slice(3,4+1)
IDX_NUM_TX_PKT  = slice(5,6+1)
IDX_NUM_TX_ACK  = slice(7,8+1)
IDX_NUM_RETRANS = slice(9,10+1)


# ACK_TYPE
ACK_NONE = 0
ACK_PLAIN = 1


# Named Tuples
#tupPktStat = namedtuple('tupPktStat','rxPkt rxAck txPkt txAck')
@dataclass
class pktStat(object):
    rxPkt:   int
    rxAck:   int
    txPkt:   int
    txAck:   int
    retrans: int
    
@dataclass
class transParam(object):
    camModemId:         int
    hardAck:            bool
    payloadLength:      int
    ackTimeout:         int
    numRetransmissions: int
    logging:            bool
    
@dataclass
class imgParam(object):
    size:        tuple
    quality:     int
    progressive: bool
    useFlash:    bool
    useCamera:   bool

class ImageTx():
    
    def __init__(self, dev, confFile = None):
        
        # conf
        self.confFile = confFile
        
        self.transParam = transParam(0,0,0,0,0,0)
        self.imgParam = imgParam((0,0),0,0,0,0)
        self.imgParamDflt = imgParam((0,0),0,0,0,0) # default image parameters
        rxGain, agc, txGain, bitSpread = self._loadConfig()
        
        # modem
        self.myModem = Modem()
        self.myModem.connect(dev)
        self.myModem.setRxEcho(True)
        self.myModem.addRxCallback(self._receive)
        self.myModem.receive(thread = True)
        
        self._initModem(rxGain, agc, txGain, bitSpread)        
        
        self.pktStat = pktStat(0,0,0,0,0)
        
        # receiving mode
        self.numHeadPkt = 0
        self.numDataPkt = 0
        self.numRxImgPkt = 0
        
        self.dstId = 0xFF # modem ID of the other station
        
        
        self.gui = None
              
        self.imgStream = jfif_splitter.jfif_splitter(progressive=self.imgParamDflt.progressive)
        
        # status
        self.ackStatus = ''
        self.status = 'IDLE' # 'IDLE','IMAGE_REQUEST','TX_IMAGE','RX_IMAGE'
                
        # threading lock
        self.lock = threading.Lock()
        # transmission Thread
        self.runTransThread = True
        self.transThread = threading.Thread(target=self._transmissionThread)
        self.transThread.start()
        # receiving timeout
        self.receivingTimeoutTimer = None
        
    def __del__(self):
        self.close()
        
    def _loadConfig(self):
        if self.confFile is None:
            print("ERROR: no config file given")
            exit(1)
        config = configparser.ConfigParser()
        print("reading config from file '%s'" % (self.confFile))
        config.read(self.confFile)

        
        # Modem Parameters
        rxGain    = config['MODEM_PARAMETERS'].getint('rxGain')
        agc       = config['MODEM_PARAMETERS'].getboolean('agc')
        txGain    = config['MODEM_PARAMETERS'].getint('txGain')
        bitSpread = config['MODEM_PARAMETERS'].getint('bitSpread')
        # Transmission Parameters
        self.transParam.camModemId            = config['TRANSMISSION_PARAMETERS'].getint('camModemId')
        self.transParam.hardAck               = config['TRANSMISSION_PARAMETERS'].getboolean('hardAck')
        self.transParam.payloadLength         = config['TRANSMISSION_PARAMETERS'].getint('payloadLength')
        self.transParam.ackTimeout            = config['TRANSMISSION_PARAMETERS'].getfloat('ackTimeout')
        self.transParam.numRetransmissions    = config['TRANSMISSION_PARAMETERS'].getint('numRetransmissions')
        self.transParam.logging               = config['TRANSMISSION_PARAMETERS'].getboolean('logging')
        if not self.transParam.hardAck:
            self.transParam.camModemId = 0xFF # broadcast to supress hard ACKs
        # Image Paramerts
        size                       = list(map(int, config['IMAGE_PARAMETERS']['size'].split(',')))
        self.imgParamDflt.size      = (size[0],size[1])
        self.imgParamDflt.quality   = config['IMAGE_PARAMETERS'].getint('quality')
        self.imgParamDflt.progressive  = config['IMAGE_PARAMETERS'].getboolean('progressive')
        self.imgParamDflt.useFlash     = config['IMAGE_PARAMETERS'].getboolean('useFlash')
        self.imgParamDflt.useCamera    = config['IMAGE_PARAMETERS'].getboolean('useCamera')
        
        return rxGain, agc, txGain, bitSpread
        
    def _initModem(self,rxGain,agc,txGain,bitSpread):
        if self.transParam.logging:
            self.timeStr = "{}".format(time.strftime("%Y%m%d-%H%M%S"))
            filename = self.timeStr
            filename += "_packets.log"
            self.myModem.logOn(file_name=filename)
        
        self.myModem.id()
        self.myModem.getVersion()
        self.myModem.getConfig()
        self.myModem.bitSpread(bitSpread)
        self.myModem.txGain(txGain)
        if agc:
            self.myModem.agc(1)
            self.myModem.rxGain()
        else:
            self.myModem.agc(0)
            self.myModem.rxGain(rxGain)
            
        self._clearModemStats()
        self._getModemStats()
        
        
    def _clearModemStats(self):
        self.myModem.clearPacketStat()
        self.myModem.clearSyncStat()
        self.myModem.clearSfdStat()
        
        self.pktStat = pktStat(0,0,0,0,0)
        
        
    def _getModemStats(self):
        self.myModem.getPacketStat()
        self.myModem.getSyncStat()
        self.myModem.getSfdStat()
        self.myModem.getPowerLevel()
        self.myModem.rxThresh()
        self.myModem.rxLevel()
        
                
        
    def _send(self,dst,payload,type,status,dsn):
        
        self.myModem.send(0x00, dst,type, payload, status, dsn)
        self.pktStat.txPkt += 1        
        if status == ACK_PLAIN:
            t = threading.Timer(self.transParam.ackTimeout,self._transmissionTimeout)
            t.start()
            self.ackStatus = 'WAITING'
            numTrans = 1
            while True:
                self.lock.acquire()
                localAckStatus = self.ackStatus
                self.lock.release()
                if localAckStatus == 'RETRANSMISSIOM':
                    print('retransmission')
                    self.myModem.send(0x00, dst,type, payload, status, dsn)
                    self.pktStat.txPkt += 1  
                    self.pktStat.retrans += 1 
                    numTrans += 1
                    self.ackStatus = 'WAITING'
                    t = threading.Timer(self.transParam.ackTimeout,self._transmissionTimeout)
                    t.start()
                if localAckStatus == 'RECEIVED':
                    t.cancel()
                    return True
                if (numTrans == self.transParam.numRetransmissions) and (localAckStatus == 'RETRANSMISSIOM'):
                    print('ERROR: max number of retransmissions')
                    return False
                time.sleep(0.01)
     
    def _sendAck(self):  
        self.myModem.send(0x00, 0xFF,TYPE_SOFT_ACK, bytes(0),ACK_NONE, 0) 
        self.pktStat.txAck += 1        
    
    def _transmissionTimeout(self):
        self.lock.acquire()
        self.ackStatus = 'RETRANSMISSIOM' 
        self.lock.release() 
    
    def _startReceivingTimeoutTimer(self):
        self.receivingTimeoutTimer = None # reset timer
        t = self.transParam.ackTimeout*(self.transParam.numRetransmissions+1) + 1
        self.receivingTimeoutTimer = threading.Timer(t,self._receivingTimeout)    
        self.receivingTimeoutTimer.start()
        
    def _receivingTimeout(self):
        self.lock.acquire()
        self.status = 'IDLE'
        self.lock.release()
        print('ERROR: receiving timeout')
        stat = pktStat(0,0,0,0,0)
        self._endImgReceiving(stat)
        
        
    def _receive(self,pkt):
        if (pkt.header.status == ACK_PLAIN) and (not self.transParam.hardAck):
            self._sendAck()
        if (pkt.header.status == ACK_PLAIN) and self.transParam.hardAck:
            self.pktStat.txAck += 1  
        if (pkt.header.type == TYPE_SOFT_ACK) or (pkt.header.type == TYPE_HARD_ACK): # TODO: check modem IDs
            self.pktStat.rxAck += 1
            if SIMULATION:
                time.sleep(0.1)
            self.lock.acquire()
            self.ackStatus = 'RECEIVED'
            self.lock.release()
        if pkt.header.type == TYPE_CMD:
            self.pktStat.rxPkt += 1
            self._processCmd(pkt.header.src,pkt.payload)
        if pkt.header.type == TYPE_DATA:
            self.pktStat.rxPkt += 1
            self.lock.acquire()
            localStatus = self.status
            self.lock.release()
            if localStatus == 'RX_IMAGE':
                self._processImgPayload(pkt.header.dsn,pkt.payload)       
        
        
    def _processCmd(self,src,payload):
        if payload[IDX_TYPE] == CMD_CAP:
            x = int.from_bytes(payload[IDX_SIZE_X],'big')
            y = int.from_bytes(payload[IDX_SIZE_Y],'big')
            self.imgParam.size = (x,y)
            self.imgParam.quality = payload[IDX_QUAL]
            self.imgParam.useFlash = payload[IDX_FLASH]
            
            self.dstId = src
            if not self.transParam.hardAck:
                self.dstId = 0xFF
            
            self.lock.acquire()
            self.status = 'IMAGE_REQUEST'
            self.lock.release()
        
        if payload[IDX_TYPE] == CMD_BEGIN:
            self.numHeadPkt = int.from_bytes(payload[IDX_NUM_HEAD],'big')
            self.numDataPkt = int.from_bytes(payload[IDX_NUM_DATA],'big')
            self.numRxImgPkt = 0
            
            self.lock.acquire()
            self.status = 'RX_IMAGE'
            self.lock.release()
            
            self._startImgReceiving()
            
        if payload[IDX_TYPE] == CMD_END:
            rxPktStat = pktStat(0,0,0,0,0)
            rxPktStat.rxPkt   = int.from_bytes(payload[IDX_NUM_RX_PKT],'big')
            rxPktStat.rxAck   = int.from_bytes(payload[IDX_NUM_RX_ACK],'big')
            rxPktStat.txPkt   = int.from_bytes(payload[IDX_NUM_TX_PKT],'big')
            rxPktStat.txAck   = int.from_bytes(payload[IDX_NUM_TX_ACK],'big')
            rxPktStat.retrans = int.from_bytes(payload[IDX_NUM_RETRANS],'big')
            self._endImgReceiving(rxPktStat)
     
        
    def _startImgReceiving(self):
        if self.gui is None:
            self.gui = imageviewer.imageviewer()
        else:
            self.gui.close()
            self.gui = None
            time.sleep(0.1)
            self.gui = imageviewer.imageviewer()
                  
        time.sleep(0.1)
        self.gui.updateBar(0, self.numHeadPkt+self.numDataPkt)
        self.gui.resetTimer()
        self.gui.startTimer()
        
        self.imgStream.reset()
        
        self._startReceivingTimeoutTimer()
        
        
        
     
    def _startImgTransmission(self,numHeaderPkt,numDataPkt): 
        # make packet
        data = bytearray(MAX_CMD_LENGTH)
        data[IDX_TYPE] = CMD_BEGIN
        data[IDX_NUM_HEAD] = int(numHeaderPkt).to_bytes(2,'big')
        data[IDX_NUM_DATA] = int(numDataPkt).to_bytes(2,'big') 
        
        return self._send(self.dstId,data,TYPE_CMD,ACK_PLAIN,self.pktStat.txPkt % 256)
     
    def _endImgTransmission(self):
        # make packet
        data = bytearray(MAX_CMD_LENGTH)
        data[IDX_TYPE] = CMD_END
        data[IDX_NUM_RX_PKT]  = int(self.pktStat.rxPkt).to_bytes(2,'big')
        data[IDX_NUM_RX_ACK]  = int(self.pktStat.rxAck).to_bytes(2,'big') 
        data[IDX_NUM_TX_PKT]  = int(self.pktStat.txPkt).to_bytes(2,'big')
        data[IDX_NUM_TX_ACK]  = int(self.pktStat.txAck).to_bytes(2,'big') 
        data[IDX_NUM_RETRANS] = int(self.pktStat.retrans).to_bytes(2,'big') 
        
        return self._send(self.dstId,data,TYPE_CMD,ACK_PLAIN,self.pktStat.txPkt % 256)  
    
    def _endImgReceiving(self,rxPktStat): 
        
        self.gui.stopTimer()
        proTime = self.gui.getTimerValue()
        proTime = round(proTime/60) # min
        
        self.receivingTimeoutTimer.cancel()
        
        print('')
        print('### Image received ###')
        print('Image-Receiver: ', self.pktStat)
        print('Image-Transmitter: ', rxPktStat)
        print('Note: Img-Transmitter transmits pktStat with the last packet (->  txPkt, rxAck and retrans from this packet is missing in pktStat)')
        print('Image-Size: ', self.imgStream.getHeaderSize() + self.imgStream.getDataSize(), 'Bytes')
        print('Transmission time: ', proTime, 'min')
        print('#######################')
        print('')
        
        if self.transParam.logging:
            img = self.imgStream.getImage()
            if img is not None:
                filename = self.timeStr + "_rxImg.jpg"
                i = 0
                while os.path.isfile(filename):
                    i += 1
                    filename = self.timeStr + '_rxImg({}).jpg'.format(i)                  
                img.save(filename)                
                # create transmission info file
                if i == 0:
                    filename = self.timeStr + "_info.log"
                else:
                    filename = self.timeStr + "_info({}).log".format(i)                  
                file = open(filename,'w+')
                file.write("### Image Info ### \n")
                file.write("Size:        {}x{} Pixel \n".format(self.imgParam.size[0],self.imgParam.size[1]))
                file.write("Quality:     {} % \n".format(self.imgParam.quality))
                file.write("Flash:       {}  \n".format(self.imgParam.useFlash))
                file.write("Progressive: {}  \n".format(self.imgParamDflt.progressive))
                file.write("Data Size:   {} Byte \n".format(self.imgStream.getHeaderSize() + self.imgStream.getDataSize()))
                file.write("\n")
                file.write("### Transmission Info ### \n")
                file.write("Payload:             {} Byte \n".format(self.transParam.payloadLength))
                file.write("Hard-ACKs:           {} \n".format(self.transParam.hardAck))
                file.write("ACK timeout:         {} s \n".format(self.transParam.ackTimeout))
                file.write("Max retransmissions: {} \n".format(self.transParam.numRetransmissions))
                file.write("\n")
                file.write("Img-Receiver:    rxPkt ={:4d}, rxAck ={:4d}, txPkt ={:4d}, txAck ={:4d}, retrans ={:4d} \n".format(self.pktStat.rxPkt, self.pktStat.rxAck,self.pktStat.txPkt,self.pktStat.txAck,self.pktStat.retrans))
                file.write("Img-Transmitter: rxPkt ={:4d}, rxAck ={:4d}, txPkt ={:4d}, txAck ={:4d}, retrans ={:4d} \n".format(rxPktStat.rxPkt, rxPktStat.rxAck,rxPktStat.txPkt,rxPktStat.txAck,rxPktStat.retrans))
                file.write("Note: Img-Transmitter transmits pktStat with the last packet (->  txPkt, rxAck and retrans from this packet is missing in pktStat) \n")
                file.write("\n")
                file.write("Time:      {} min \n".format(proTime))
                file.flush()
                os.fsync(file.fileno())
                file.close()
            
        # get and reset status 
        self._getModemStats()
        self._clearModemStats()
         
        self.lock.acquire()
        self.status = 'IDLE'
        self.lock.release()
        
    def _processImgPayload(self,dsn,payload):
        
        if dsn != (self.numRxImgPkt % 256):
            #print("doppeltes paket")
            return
        
        self.receivingTimeoutTimer.cancel()        
        self.numRxImgPkt += 1                
        
        if self.numRxImgPkt <= self.numHeadPkt:
            self.imgStream.addHeader(payload)
        if self.numRxImgPkt == self.numHeadPkt +1:           
                        
            self.imgStream.headerFinish()
            self.imgStream.addData(payload)
            
            img = self.imgStream.getImage()
            if img is not None:
                self.gui.updateImage(img)
                self.gui.resizeToImg()
                
        if self.numRxImgPkt > self.numHeadPkt +1:
            self.imgStream.addData(payload)
            
            img = self.imgStream.getImage()
            if img is not None:
                self.gui.updateImage(img)    
            
        self.gui.updateBar(self.numRxImgPkt)
        
        self._startReceivingTimeoutTimer()
        
        
    
    def transmitImg(self):
        cam = camera.camera()
        img = cam.capture(self.imgParam.size,self.imgParam.useFlash)
        
        
        if self.transParam.logging:
            filename = self.timeStr + '_capImg.jpg'
            i = 0
            while os.path.isfile(filename):
                i += 1
                filename = self.timeStr + '_capImg({}).jpg'.format(i)                
            img.save(filename)
        
        self.imgStream.setImage(img,self.imgParam.size,self.imgParam.quality)
        
        headerSize = self.imgStream.getHeaderSize()
        dataSize   = self.imgStream.getDataSize()
        
        print('Picture captured. Size: {} Bytes \n'.format(headerSize+dataSize))
        
        numHeaderPkt = int(math.ceil(headerSize/self.transParam.payloadLength))
        numDataPkt = int(math.ceil(dataSize/self.transParam.payloadLength))
        
        if not self._startImgTransmission(numHeaderPkt, numDataPkt):
            return
        
        dsn = 0
        # transmit header
        header = self.imgStream.getHeader()
        for i in range(0,numHeaderPkt):
            idx1 = int(i*self.transParam.payloadLength)
            if (i+1)*self.transParam.payloadLength-1 > len(header):
                idx2 = int(len(header))
            else:
                idx2 = int((i+1)*self.transParam.payloadLength)
                
            if not self._send(self.dstId,header[idx1:idx2], TYPE_DATA, ACK_PLAIN,dsn%256):
                return            
            dsn += 1
            
        # transmit data
        data = self.imgStream.getData()
        for i in range(0,numDataPkt):
            idx1 = int(i*self.transParam.payloadLength)
            if (i+1)*self.transParam.payloadLength-1 > len(data):
                idx2 = int(len(data))
            else:
                idx2 = int((i+1)*self.transParam.payloadLength)
                
            if not self._send(self.dstId,data[idx1:idx2], TYPE_DATA, ACK_PLAIN,dsn%256):
                return 
            dsn += 1
            
        self._endImgTransmission()
        
        # get and reset status 
        self._getModemStats()
        self._clearModemStats()
        
        self.status = 'IDLE'
        print("Image transmitted")
        
        
        
    def requestImg(self,size = None,quality = None,flash = None):        
        if size is None:
            size = self.imgParamDflt.size
        if quality is None:
            quality = self.imgParamDflt.quality
        if flash is None:
            flash = self.imgParamDflt.useFlash
            
        self.reqTime = time.time()
            
        # make packet
        data = bytearray(MAX_CMD_LENGTH)
        data[IDX_TYPE] = CMD_CAP
        data[IDX_SIZE_X] = int(size[0]).to_bytes(2,'big')
        data[IDX_SIZE_Y] = int(size[1]).to_bytes(2,'big')
        data[IDX_QUAL] = quality
        data[IDX_FLASH] = int(flash)
        
        # store for info log
        self.imgParam.size = size;
        self.imgParam.quality = quality;
        self.imgParam.useFlash = flash;
        
        
        if self._send(self.transParam.camModemId,data,TYPE_CMD,ACK_PLAIN,self.pktStat.txPkt % 256):
            print('Image request received')
        else:
            print('Image request FAILED')
    
    def _transmissionThread(self):
        run = True
        while run:
            if self.imgRequestReceived():
                self.transmitImg()
                self.lock.acquire()
                self.status = 'IDLE'
                self.lock.release()
            time.sleep(0.1)
            self.lock.acquire()
            run = self.runTransThread
            self.lock.release() 
    
       
    def imgRequestReceived(self):  
        self.lock.acquire()
        req = self.status == 'IMAGE_REQUEST'
        self.lock.release() 
        return req
        
    def close(self):
        time.sleep(1)
        self.lock.acquire()
        self.runTransThread = False
        self.lock.release()
        self.transThread.join(1)
        if self.gui is not None:
            self.gui.close()
        if self.myModem is not None:
            if self.transParam.logging:
                self.myModem.logOff()
            self.myModem.close()
            self.myModem = None
        
        
        
