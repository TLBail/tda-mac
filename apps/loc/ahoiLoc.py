#! /usr/bin/env python3

#
# Copyright 2019
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

"""Simple localization script using lateration (based on at least 3 anchors)."""

from __future__ import print_function

import numpy as np
import math

import threading
import configparser
import struct

from ahoi.modem.modem import Modem


class Anchor3D:
  """3-D position plus modem id and distance"""
  def __init__(self, id, x, y, z):
    self.id = id
    self.x  = x
    self.y  = y
    self.z  = z
    self.d  = -1  # negative value to indicate n.a.



class Robot:
  def __init__(self, z, com):
    self.r = 0  # round
    self.z = 0  # depth
    self.tofOffset = 0 # offset of TOF values (should be done by modem => 0)
    # connect to modem
    self.modem = Modem()
    self.modem.connect(com)
    self.modem.addRxCallback(self.__handlePkt)
    self.modem.setTxEcho(True)
    self.modem.setRxEcho(True)
    self.modem.receive(True) # receive non-blocking (as thread)
    
    
  def runLoc(self, intvl = 5.0, pktType = 0, anchors = [], sos = 1450.0):
    self.intvl = intvl
    self.pktType = pktType
    self.A = anchors
    self.sos = sos
    
    self.__loc()
    
    
  def __loc(self):
    # attempt localization
    if self.r > 0:
      print("\n=== round %u ===" % (self.r))
      self.__locLat()
    
    # TODO convert to absolute position?
    # TODO convert to lat/lon?
    # TODO post result to appropriate place
      
    # send new ping
    self.modem.send(type=self.pktType, src=0, dst=255, dsn=(self.r%256), status=2, payload=bytearray())
    
    # next round
    self.r = self.r + 1
    for a in self.A:
      a.d = -1
    
    # delay
    timer = threading.Timer(self.intvl, self.__loc) 
    timer.start()
  
  
  # lateration: localization of anchors (array of array) and robot with known depth z
  def __locLat(self):
    # how many responses?
    R = []
    for i in range(0,len(self.A)):
      if self.A[i].d >= 0:
        R.append(i)
    N = len(R)

    # sanity check
    if (N < 3):
      print("cannot determine position with less than 3 anchors!")  # TODO raise error
      return

    ## prepare matrix
    M = np.empty([N-1, 2], dtype=float)
    b = np.empty([N-1, 1], dtype=float)
    a0 = self.A[R[0]]
    rr0 = -a0.d**2 + (a0.z - self.z)**2 + a0.x**2 + a0.y**2
    for i in range(1,N):
      ai = self.A[R[i]]
      rri = ai.d**2 - (ai.z - self.z)**2
      M[i-1][0] = 2 * (a0.x - ai.x)
      M[i-1][1] = 2 * (a0.y - ai.y)
      b[i-1] = rri + rr0 - a0.x**2 - ai.y**2
      #print(M[i-1], b[i-1])

    ## solve with BLAS
    self.x, self.y = np.linalg.lstsq(M, b, rcond=None)[0]
    ###px, py = np.linalg.lstsq(M, b, rcond=0.0)[0]
    print("estimated position: %g, %g" % (self.x, self.y))
    
    
  # handle ranging acks
  def __handlePkt(self, pkt):
    if pkt.header.type != 0x7F or pkt.header.len == 0:
      return
    
    # find anchor in list
    ac = None
    for a in self.A:
      #print("%u vs %u" % (a.id, pkt.header.src))
      if a.id == pkt.header.src:
        ac = a
        break
    
    if ac is None:
      return
    
    # extract TOF from packet (average TOF, modem already divides by 2.0)
    tofBytes = pkt.payload[0:4]
    tof = struct.unpack('>L', tofBytes)[0]
    ac.d = (tof - self.tofOffset) * self.sos * 1e-6
    if ac.d < 0:
      ac.d = 0
    print("received distance from %u: %fm" % (ac.id, ac.d))


def main():
  # command line arguments
  import argparse
  parser = argparse.ArgumentParser(
    description = "AHOI localization.",
    epilog = """NOTE: this script is work-in-progress.""")

  parser.add_argument(
    '-c', '--config',
    type = str,
    default = 'config/default.ini',
    dest = 'confFile',
    help = 'config file (default: config/default.ini)'
  )

  args = parser.parse_args()
  
    # open config
  testConfig = configparser.ConfigParser()
  testConfig.read(args.confFile)

  # NETWORK
  com = testConfig['NETWORK']['com']
  
  # ANCHORS
  A = []
  a = 0
  while True:
    an = 'anchor[%u]' % a
    try:
      coords = list(map(float, testConfig['ANCHORS'][an].split(',')))
      coords[0] = int(coords[0])
      print("anchor %3u @ (%6.2f,%6.2f,%6.2f)" % (coords[0], coords[1], coords[2], coords[3]) )
      A.append(Anchor3D(coords[0], coords[1], coords[2], coords[3]))
    except:
      break
    a = a + 1
  
  # ROBOT
  depth = testConfig['ROBOT'].getfloat('depth')
  
  # LOCALIZATION
  intvl = testConfig['LOCALIZATION'].getfloat('interval')
  pktType = testConfig['LOCALIZATION'].getint('pktType')
  sos = testConfig['LOCALIZATION'].getfloat('speedOfSound')
  
  
  # start
  r = Robot(depth, com)
  r.runLoc(intvl, pktType, A, sos)


if __name__ == "__main__":
    main()

# eof
