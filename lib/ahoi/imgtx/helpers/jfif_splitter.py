#
# Copyright 2018-2019
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

from PIL import Image
from io import BytesIO


# jfif symbols
SOI = 0xD8 # Start Of Image
APP0 = 0xE0 # JFIF tag
DQT = 0xDB # def quantisation table
DHT = 0xC4 # def Huffman table
SOS = 0xDA # start of scan
EOI = 0xD9 # end of image

SOF2 = 0xC2 # progressive DCT
SOF0 = 0xC0 # Baseline DCT (sequential compression)     



class jfif_splitter():
    
    def __init__(self, progressive = True):
        
        self.imgStream = BytesIO()
        self.imgHeader = bytearray()
        self.imgData = bytearray()
        
        self.progressive = progressive; # progressive or sequential
        
        self.headerComplete = False;
        
    #def __del__(self):
        
        
    def _split(self):
        self.imgHeader = bytearray()
        self.imgData = bytearray()
                
        self.imgStream.seek(0)
        
        while self.imgStream.readable():
            b = int.from_bytes(self.imgStream.read(1),'big')
            if b == 0xFF:
                b = int.from_bytes(self.imgStream.read(1),'big')
                
                #if b == self.SOI: # TODO
                    #print('begin image stream')
                    
                # header
                if b == APP0:                                        
                    self._appendTag(self.imgHeader,b)
                if b == DQT:
                    self._appendTag(self.imgHeader,b)
                if (b == SOF2) and (self.progressive):
                    self._appendTag(self.imgHeader,b)
                if (b == SOF0) and (not self.progressive):
                    self._appendTag(self.imgHeader,b) 
                if (b == DHT) and (not self.progressive):  
                    self._appendTag(self.imgHeader,b) 
                # data
                if (b == DHT) and (self.progressive):  
                    self._appendTag(self.imgData,b)
                if b == SOS:                    
                    self._appendSOS(self.imgData)
                                        
                    
                if b == EOI:
                    break
        
        self.headerComplete = True;      
        
    def _merge(self):
        self.imgStream = BytesIO()
        # Start of Image
        self.imgStream.write(0xFF.to_bytes(1,'big'))
        self.imgStream.write(SOI.to_bytes(1,'big'))
        # Header 
        self.imgStream.write(self.imgHeader)
        # Image Data Parts
        self.imgStream.write(self.imgData)
        # End of Image
        self.imgStream.write(0xFF.to_bytes(1,'big'))
        self.imgStream.write(EOI.to_bytes(1,'big'))
        
        
        #with open('test.ext', 'wb') as f:
        #    f.write(self.imgStream.getvalue())
     
        
    def _appendTag(self,array,symbol):   
        size = self.imgStream.read(2)
        data = self.imgStream.read(int.from_bytes(size,'big')-2)
        
        array.append(0xFF)
        array.append(symbol)
        array += size
        array += data
     
        
    def _appendSOS(self,array):
        array.append(0xFF)
        array.append(SOS)
        
        while self.imgStream.readable():
            b = int.from_bytes(self.imgStream.read(1),'big')
            if b == 0xFF:
                b = int.from_bytes(self.imgStream.read(1),'big')
                if b == 0x00:
                    array.append(0xFF)
                else:
                    pos = self.imgStream.tell()
                    self.imgStream.seek(pos-2)
                    break
            array.append(b)


    
    def setImage(self,img,size = None, quality = 25):
        if size is not None:
            img = img.resize(size)
            
        self.imgStream = BytesIO()
        
        img.save(self.imgStream,'JPEG',quality=quality,progressive = self.progressive ,optimize = True,subsampling=2)        
        
        self._split()
        
        
    def getImage(self):
        if not self.headerComplete:
            return None
        
        self._merge()
        try:
            img = Image.open(self.imgStream)
        except:
            img = None
        
        return img
        
    def reset(self):
        self.imgHeader = bytearray()
        self.headerComplete = False
        self.imgData = bytearray()
        
    def addHeader(self,header,headerComp = False):
        self.imgHeader += (header)  
        self.headerComplete = headerComp
        
    def headerFinish(self):
        self.headerComplete = True
        
    def getHeader(self):
        return self.imgHeader
        
    def getHeaderSize(self):
        return len(self.imgHeader)
        
    def addData(self,data):
        self.imgData += (data)  
        
    def getData(self):
        return self.imgData
        
    def getDataSize(self):
        return len(self.imgData)
        
    
