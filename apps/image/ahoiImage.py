#! /usr/bin/env python3

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
import sys
import re
import string

from ahoi.imgtx.imgtx import ImageTx
from ahoi.com.serial import ModemSerialCom
   
    
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="AHOI image transmission application.",
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

    args = parser.parse_args()

    # connect to modem
    port = ModemSerialCom.scanAndSelect()
    imgTrans = ImageTx(port, args.confFile)
    
    while True:
        inp = input('>> ')
        
        inp = inp.strip()  # strip leading/trailing spaces
        inp = re.sub("\s{2,}", " ", inp)  # remove multiple spaces (make one)
        inp = inp.split(' ')
        cmd = inp[0]
        
        if (len(cmd) > 0 and cmd[0] != '#'):
            if cmd == 'exit' or cmd == 'quit':
                imgTrans.close()
                exit() 
                
            if cmd == 'capture':
                if len(inp) == 1:
                    imgTrans.requestImg()
                else:
                    try:
                        size = (int(inp[1]),int(inp[2]))
                        qual = int(inp[3])
                        flash = bool(inp[4])
                        imgTrans.requestImg(size,qual,flash)
                    except:
                        print('ERROR: improper parameter list!')                     
                
    
if __name__ == "__main__":
    main()
