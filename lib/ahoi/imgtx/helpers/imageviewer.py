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
import time, threading, sys, math, os


print("GUI created with the help of:") 
import pygame
from pygame.locals import *


class imageviewer():

    def __init__(self):
        
        # position settings
        self.appWidth = 600
        self.appHeight = 600
        
        self.barScale = 1/10
        #self.clockScale = 1/10
        self.imgScale = 9/10
        
        self.imgWidth = 0
        self.imgHeight = 0
        
        # default logo 
        filepath = os.path.join(os.path.dirname(__file__),'./images/smartport_800x800.png')
        logo = Image.open(filepath)
        
        # load font
        filepath = pygame.font.match_font('consolas', bold=True)
        if filepath is not None:
            self.font_filepath = filepath
        else:
            print('Can not find consolas (a nice-looking monospaced font). Using the pygame default font.')
            self.font_filepath = 'freesansbold.ttf'
        
	    # progress bar settings
        self.numPkt = 0
        self.numMaxPkt = 0   
        
        # timer settings
        self.timerVal = 0
        self.timerIsRunning = False
        
        
        self.run = True
        self.lock = threading.Lock()
        
        self.img = None
        self.pilImg = None
        
        self.updateImage(logo)
        
        
        # init monitoring thread
        self.eventThread = threading.Thread(target=self._guiProcess)
        self.eventThread.start()


    def __del__(self):
        self._close()
		
    def _close(self):
        pygame.quit() 
        #quit()       
        # waiting for thread
        #self.eventThread.join()
        
    def _convertImage(self):
        err = False
        try:
            width = self.pilImg.size[0]
            height = self.pilImg.size[1]
        
            newHeight = math.floor(self.appHeight*self.imgScale)        
            newWidth = math.floor(newHeight/height*width)
        
            if newWidth > self.appWidth:
                newWidth = self.appWidth
                newHeight = math.floor(newWidth/width*height)
        
            newImg = self.pilImg.resize((newWidth,newHeight))
        except Exception as e:
            err = True
            #print("error in _convertImage")
            #print(e)
            
        if not err:
            self.imgWidth = newWidth
            self.imgHeight = newHeight
        
            self.lock.acquire()
            self.img = pygame.image.fromstring(newImg.tobytes(),newImg.size,newImg.mode)
            self.lock.release()
    
    def _drawBar(self,xpos,ypos,width,height):
        green = (208,227,0)
        gray = (140,140,140)
        black = (0,0,0)
        unit = "Packets"
        
        self.lock.acquire()
        numPkt = self.numPkt
        numMaxPkt = self.numMaxPkt
        self.lock.release()
        
        pygame.draw.rect(self.app, gray, (xpos,ypos,width,height))
        
        offset = 3            
        if numMaxPkt is not 0:
            length = math.floor(width*numPkt/numMaxPkt) 
            if length < 2*offset:
                length = 2*offset  
        else:
            length = 2*offset
        
        xpos += offset
        ypos += offset 
        length -= 2*offset
        width -= 2*offset
        height -= 2*offset
        pygame.draw.rect(self.app, green, (xpos,ypos,length,height))
        
        # timer value
        timer = self.getTimerValue()
        minutes = math.floor(timer/60)
        sec = math.floor(timer - 60*minutes)
        
        text = '{}/{} {} (elapsed: {:d}min:{:02d}s)'.format(numPkt,numMaxPkt,unit,minutes,sec)
        offset = 4
        font = pygame.font.Font(self.font_filepath,height-2*offset)
        #font.set_bold(True)
        textSurf = font.render(text,True,black)
        textRect = textSurf.get_rect()
        cx = xpos + math.floor(width/2)
        cy = ypos + math.floor(height/2)
        textRect.center = ((cx,cy))
        self.app.blit(textSurf,textRect)
    
    #def _printClock(self,xpos,ypos,width,heigth):
    #    black = (0,0,0)
    #    
    #    clk = self.getTimerValue()
    #    
    #    text = 'Transmission Time: '
    #    offset = 1        
    #    font = pygame.font.Font('freesansbold.ttf',heigth-2*offset)
    #    textSurf = font.render(text,True,black)
    #    textRect = textSurf.get_rect()
    #    cx = xpos + math.floor(width/2)
    #    cy = ypos + math.floor(heigth/2)
    #    textRect.center = ((cx,cy))
    #    self.app.blit(textSurf,textRect)
        
        
    def _guiProcess(self):
        # create gui       
        pygame.init()
        self.app = pygame.display.set_mode((self.appWidth,self.appHeight),RESIZABLE)
        pygame.display.set_caption("AHOI Image Transmission") 
        filepath =  os.path.join(os.path.dirname(__file__),'./images/smartport_anchor_32x32.png')
        pygame.display.set_icon(pygame.image.load(filepath))      
        self.clock = pygame.time.Clock()
        
        run = True
        
        while run:
            time.sleep(0.01)
            self._guiUpdate()
            self.clock.tick(10)
            for event in pygame.event.get():
                #print(event)
                if event.type == pygame.VIDEORESIZE:
                    #print(event.size)
                    self.appWidth = event.size[0]
                    self.appHeight = event.size[1]
                    self.app = pygame.display.set_mode((self.appWidth,self.appHeight),RESIZABLE)
                    self._convertImage()
                if event.type == pygame.QUIT:
                    self.lock.acquire()
                    self.run = False
                    self.lock.release()
                    
            self.lock.acquire()
            run = self.run
            self.lock.release()
                   
        self._close()               
    
    def _guiUpdate(self):
        self.app.fill((255,255,255))
        # update image
        xpos = math.floor((self.appWidth-self.imgWidth)/2)
        ypos = math.floor(self.appHeight-self.imgHeight)
        
        self.lock.acquire()
        self.app.blit(self.img,(xpos,ypos))
        self.lock.release()
        # update progress bar
        offset = 10
        xpos = offset
        ypos = offset
        width = self.appWidth - 2*offset
        heigth = math.floor(self.barScale*self.appHeight - 2*offset)
        self._drawBar(xpos,ypos,width,heigth)
        # update timer
        #xpos = offset
        #ypos = self.barScale*self.appHeight + offset        
        #width = self.appWidth - 2*offset
        #heigth = math.floor(self.clockScale*self.appHeight - 2*offset)
        #self._printClock(xpos,ypos,width,heigth)
        
        pygame.display.update()
        
	
    def updateImage(self,pilImg):
        self.pilImg = pilImg
        self._convertImage()
        
    def updateBar(self,numPkt,numMaxPkt = None):
        self.lock.acquire()
        self.numPkt = numPkt
        if numMaxPkt is not None:
            self.numMaxPkt = numMaxPkt        
        self.lock.release()
        
    def resizeToImg(self):
        err = False
        try:
            width = self.pilImg.size[0] 
            height = math.ceil(self.pilImg.size[1] / self.imgScale)
        except:
            err = True
        
        if not err:
            self.lock.acquire()
            self.appWidth = width
            self.appHeight = height
            resizeEvent = pygame.event.Event(pygame.VIDEORESIZE,size=(width,height),w=width,h=height)
            pygame.event.post(resizeEvent)
            self.lock.release()
        
        
    def isRunning(self):
        self.lock.acquire()
        run = self.run
        self.lock.release()
        return run
    
    def close(self):
        self.lock.acquire()
        self.run = False
        self.lock.release()
        self.eventThread.join()
        
        
    def startTimer(self):
        self.lock.acquire()
        self.timerIsRunning = True
        self.timerVal = time.time()
        self.lock.release()
        
        
    def stopTimer(self):
        self.lock.acquire()
        self.timerIsRunning = False
        self.timerVal = time.time() - self.timerVal
        self.lock.release()
        
        
    def resetTimer(self):
        self.lock.acquire()
        self.timerIsRunning = False
        self.timerVal = 0
        self.lock.release()
        
        
    def getTimerValue(self):
        self.lock.acquire()
        if self.timerIsRunning:
            res = time.time() - self.timerVal 
        else:
            res = self.timerVal
        self.lock.release()    
        return res




		
