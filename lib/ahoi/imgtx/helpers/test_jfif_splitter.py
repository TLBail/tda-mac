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
import jfif_splitter
import time
from math import ceil
import imageviewer

progressive = True
#progressive = False

im = Image.open("images/underwater1_1920x1440.jpg")
imgTx = jfif_splitter.jfif_splitter(progressive)
imgRx = jfif_splitter.jfif_splitter(progressive)

gui = imageviewer.imageviewer()

imgTx.setImage(im,(640,480))

print(imgTx.getHeaderSize())
print(imgTx.getDataSize())

payloadSize = 64 # Byte
delay = 0.1

header = imgTx.getHeader()
data = imgTx.getData()

numHeaderPkt = int(ceil(len(header)/payloadSize))
numDataPkt = int(ceil(len(data)/payloadSize))

gui.updateBar(0, numHeaderPkt+numDataPkt)
gui.startTimer()

# transmit header
for i in range(0,numHeaderPkt):
    idx1 = int(i*payloadSize)
    if (i+1)*payloadSize-1 > len(header):
        idx2 = int(len(header))
    else:
        idx2 = int((i+1)*payloadSize)
       
    imgRx.addHeader(header[idx1:idx2])
    im = imgRx.getImage()
    if im is not None:
        gui.updateImage(im)
    gui.updateBar(i+1)
    time.sleep(delay)

imgRx.headerFinish()

# transmit data
for i in range(0,numDataPkt):
    idx1 = int(i*payloadSize)
    if (i+1)*payloadSize-1 > len(data):
        idx2 = int(len(data))
    else:
        idx2 = int((i+1)*payloadSize)
       
    imgRx.addData(data[idx1:idx2])
    im = imgRx.getImage()
    if im is not None:
        gui.updateImage(im)
    gui.updateBar(i+1+numHeaderPkt)
    if i == 0:
        gui.resizeToImg()
    time.sleep(delay)

gui.stopTimer()
print("finish")    

while gui.isRunning():
    time.sleep(0.1)
