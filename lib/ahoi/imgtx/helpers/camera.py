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

import time
import os
from PIL import Image
from io import BytesIO
try:
    from picamera import PiCamera
    import RPi.GPIO as GPIO
except ImportError:
    print("cannot import PiCamera and GPIO")
    
FLASH_PIN = 17

#DEBUG_IMAGE = './images/underwater2_1920x1920.jpg' #  1:1
DEBUG_IMAGE = './images/underwater2_1920x1440.jpg' #  4:3
#DEBUG_IMAGE = './images/underwater2_1920x1080.jpg' # 16:9

    
class camera():
    
    def __init__(self,useCamera = True, useFlash = True):
        self.useCamera = useCamera
        self.useFlash = useFlash
        
        if self.useCamera:
            try:
                self.cam = PiCamera()
            except:
                self.useCamera = False
                
        if self.useFlash:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(FLASH_PIN, GPIO.OUT)
            except:
                self.useFlash = False
            
                    
    def __del__(self):
        if self.useFlash:
            GPIO.cleanup()
    
    def _flashOn(self):
        if self.useFlash:
            GPIO.output(FLASH_PIN,GPIO.HIGH)
            time.sleep(0.5)
        
    def _flashOff(self):
        if self.useFlash:
            time.sleep(0.1)
            GPIO.output(FLASH_PIN,GPIO.LOW)
        
    def capture(self,size,flash = None):
        if self.useCamera:
            stream = BytesIO()
            self.cam.resolution = size
            self.cam.start_preview()
            # camera warmup
            time.sleep(2)
            if flash:
                self._flashOn()
            self.cam.capture(stream, format='jpeg')
            stream.seek(0)
            if flash:
                self._flashOff()
            image = Image.open(stream)
            self.cam.stop_preview()
        else:
            filepath = os.path.join(os.path.dirname(__file__),DEBUG_IMAGE)
            image = Image.open(filepath)
            image = image.resize(size)
            
        return image
