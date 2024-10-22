#!/usr/bin/env python3

"""Visualize sample data from modem and export to image file"""

import os
import argparse

from ahoi.handlers.SamplePlotHandler import SamplePlotHandler as SampleHandler
#from ahoi.handlers.SampleHandler import SampleHandler
from ahoi.modem.packet import byteArrayToPacket



def process(file, show):
    try:
        #data = np.loadtxt(file)
        f = open(file, 'r')
    except:
        print("ERROR: Could not read file '%s' (skipped)" % file)
        return
    
    sh = SampleHandler(show = show)
        
    # TODO move this in standalone lib class
    i = 0
    for l in f:
        # remove newline and skip empty lines
        l = l.rstrip()
        if not len(l) > 0:
            continue
        
        # pkt octets (first fields is timestamp, following ones are pkt data)
        o = l.split()[1:]        # space-separated octets to list
        b = bytearray.fromhex(''.join(o)) # octets to byte array
        pkt = byteArrayToPacket(b)        # byte array to packet
        
        # feed packet to sample handler
        ret = sh.handlePkt(pkt)
        
        if ret and sh.isComplete():
            fn = os.path.splitext(file)[0] + '-%03u.dat' % (i)
            i = i + 1
            print("saving sample data to '%s'" % (fn))
            #sh.save(fn)
            fh = open(fn, 'w')
            for d in sh.data:
                fh.write(str(d)+'\n')
            fh.close()
            
            if show:
                #sh.plot()
                input("Press Enter to continue ...")
                sh.close()
            
                      
    ## Preprocess data
    ## Values are in the interval [-16384, 16383]
    #data = data / 16384
    #data = data - np.mean(data)
    #data = data.tolist()  # PlotHandler expects a list

    ## Get standard deviation before zero padding
    #stddev = np.std(data)

    ## Check if data length is power of 2 and pad with zeros
    #opt_len = 1
    #while opt_len < len(data):
        #opt_len = opt_len * 2
    #if len(data) != opt_len:
        #print(
            #"WARNING: Number of samples (%i) not power of 2 in %s" % (len(data), file)
        #)
    #nprepend = (opt_len - len(data)) // 2
    #prepend = [0] * nprepend
    #nappend = opt_len - len(data) - nprepend
    #append = [0] * nappend
    #data = prepend + data + append

    ## Choose sensible file name for output file
    #outfile = file
    #if outfile.endswith(".dat") and len(outfile) > 4:
        #outfile = outfile[:-4]
    #outfile = outfile + ".png"

    ## Inject data into plotting class
    #sph = PlotHandler()
    #sph.numTotal = len(data)
    #sph.data = data
    ##sph.plot()

    ## Write the file name in the plot
    #plottext = file
    #ilast = file.rfind("/")
    #if ilast != -1 and len(file) > 1:
        #plottext = plottext[ilast + 1 :]
    #sph.axs[0].text(1, 0.85, plottext)

    ## Write the standard deviation in the plot
    #sph.axs[0].text(1, 0.7, "std dev: %.3f" % stddev)

    #sph.axs[0].grid(alpha=0.5)
    #sph.axs[1].grid()

    ## Save
    #plt.savefig(outfile, dpi=200)
    #plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="sample2dat",
        epilog="""\
          NOTE: no security measures are implemented.
          Input is not validated.""")
    
    parser.add_argument(
        '-s', '--show',
        action='store_true',
        dest = 'show',
        help = 'flag to show sampled data (one by one)'
        )
    
    parser.add_argument(
        nargs = '+',
        type = str,
        default = None,
        dest = 'files',
        metavar = 'files',
        help = 'list of files to be parsed')
    
    args = parser.parse_args()
    
    for f in args.files:
        process(f, args.show)
    
