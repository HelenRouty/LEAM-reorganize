import sys
sys.path += ['..']
import pandas as pd
import numpy as np
from sets import Set

SIMMAPHEADER = "./Inputs/simMapheader.txt"

def genSimMap_results(spatialcode, classColorCondlist, filename):
    """ I change Youshan's code for growth from darker blue to light blue- for years of growth
    This function generates simMap: the meta data for maps projected on google map
       for SimMap add-on for Plone.
       @inputs: 1. spatial code: a code string for each UTM Zone.
                For example, Chicago in UTM Zone 16N: 26916.
                [http://sdmdataaccess.nrcs.usda.gov/SpatialReferenceHelp.htm]
                2. classColorCondlist: a string triplet list of (classname, condition, RGB)
                Sample condition can be "> 50". RGB colors is represented as a string with 
                R, G, B numerical values seperated by a space.
                3. filename: the map name of the simMap file to output.
       @output: the simMap file with filename and postfix .map into ./Outputs folder.
    """
    # get header and footer from simMapheader.txt
    with open (SIMMAPHEADER) as f:
        lines = f.readlines()
    header = lines[:-2]
    footer = lines[-2:]
    #Note that, in the simMapheader.txt, the layer name has to be final4 as 
    #defined in /services/plone/chicago/zinstance/src/leam.simmap/leam/
    #simmap/browser/simmap.js.

    # generate strings for each class color
    classcolor_list = []
    for classname, cond, color in classColorCondlist:
        classcolor_list.append ('\
    CLASS\n\
      NAME "class%s"\n\
      EXPRESSION (%s)\n\
      STYLE\n\
        COLOR %s\n\
      END\n\
    END\n\n' % (classname, cond, color))

    # generate projection location
    projection = '\
    PROJECTION\n\
      "init=epsg:%s"\n\
    END\n' % (spatialcode)

    classcolor_list.append(projection)

    # write strings to filename.map
    outdata = "".join(header + classcolor_list + footer)
    outfilename = "Outputs/"+ filename + ".map"
    with open(outfilename, "w") as f:
      f.writelines(outdata)

def getQuantileList(mapfilename, numbaskets, nomin=False, nomax=False, isuniq=False):
    """Get the list of ticks for color assignment.
       @inputs: mapfilename(str): the ascii map to be read
                numbaskets(int): the number of colors expected to assgin.
                                 This number may decrease after quantile.
                                 This value is useless if isuniq is set.
                isuniq (bool): if isuniq = True, return uniq values
                               Otherwise, return quantile ticks.
                nomax (bool): if nomax = True, max value has no color assignemd.
                nomin (bool):  if nomin = True, min value has no color assigned.
        @outputs: arrticks (list of int): the list of ticks to assign color
                  numbaskets(int): number of ticks used.
    """
    df = pd.read_csv(mapfilename, sep=r"\s+", skiprows=6, header=None)
    arr = df.values.flatten()
    arr =  arr[arr>=0] # mapserver cannot recognize negatives
    basketsize = len(arr)/numbaskets
    sortedarr = np.sort(arr)

    # if the number of uniq values is less than 30, then return 
    # the uniq values directly. Thus, maps composed of only 0 and 1
    # can be colored without losing its base values.
    uniqarr = np.unique(sortedarr)
    if isuniq or len(uniqarr) <= 31:
        if nomin:
            #print "minValue", uniqarr[0]
            #print "otherValue", uniqarr[1:]
            return uniqarr[uniqarr!=uniqarr[0]], True
        if nomax:
            return uniqarr[uniqarr!=uniqarr[-1]], True
        return uniqarr, True # set isuniq to be true

    # if the maximum values has more than a quanter number of basketsize, 
    # 15 baskets may become [1, max, max, max, max] only
    # without intermediate values.
    removemax = False
    if nomax or len(sortedarr[sortedarr == sortedarr[-1]]) > (numbaskets>>2)*basketsize:
        sortedarr = sortedarr[sortedarr!= sortedarr[-1]]
        basketsize = len(sortedarr)/numbaskets
        removemax = True

    # if the minumum values has more than a quanter number of basketsize,
    # 15 baskets may become [min, min, min, min, 9] only
    # without intermediate values.
    removemin = False
    if nomin or len(sortedarr[sortedarr == sortedarr[0]]) > (numbaskets>>2)*basketsize:
        sortedarr = sortedarr[sortedarr!=sortedarr[-1]]
        basketsize = len(sortedarr)/numbaskets
        removemin = True

    # if removemin and not nomin: # add minimum value to it
    # if removemax and not nomax: # add maximum value to it
    arrticks = sortedarr[0:-1:basketsize]
    if arrticks[-1] > 1:
        arrticks = arrticks.astype(int)
    arrticks = np.unique(arrticks)
    print basketsize
    print arrticks
    return list(arrticks), False # return isuniq to be False

def getRGBList(numbaskets):
    """Inteporlate colors for maximum values to minimum values
       with colors with red to yellow to green to blue.
       @input: numbaskets(int): number of colors
       @output: rgblist(list of str): list of 'R G B' codes
    """
    if numbaskets == 1:
        return ['255 0 0']
    if numbaskets == 2:
        return ['255 255 0', '255 0 0']
    if numbaskets == 3:
        return ['220 220 240', '115 120 150', '10 20 60']
    if numbaskets == 4:
        return ['220 220 240', '150 160 180', '807 85 120', '10 20 60']

    # From dark blue (early years) to light blue (late years).
    # Red Color Code List
    rnum50 = rnum255 = max(0, numbaskets/3-1)
    rarr = np.linspace(10, 220, numbaskets-rnum50-rnum255, dtype=np.int)
    rlist = [10]*rnum50 + rarr.tolist() + [220]*rnum255
    rlist = rlist[::-1]

    # Green Color Code List
    gnum50 = gnum255 = max(0, numbaskets / 3 - 1)
    garr = np.linspace(20, 220, numbaskets - gnum50 - gnum255, dtype=np.int)
    glist = [20] * gnum50 + garr.tolist() + [220] * gnum255
    glist = glist[::-1]

    # Blue Color Code List
    bnum50 = bnum255 = max(0, numbaskets/3-1)
    barr = np.linspace(60, 240, numbaskets-bnum50-bnum255, dtype=np.int)
    blist = [60]*bnum50 + barr.tolist() + [240]*bnum255
    blist = blist[::-1]

    rgblist = []
    for i in xrange(numbaskets):
        rgblist.append(str(rlist[i]) + " " + str(glist[i]) + " " + str(blist[i]))
    return rgblist

def genclassColorCondlist_results(filename, numbaskets, nomin=False, nomax=False, isuniq=False):
    """Generate a list of triples in the format(classname, condition, color)
       @inputs: filename(str): the ascii map filename without path and postfix,
                              which is a .txt file locates in ./Data directory.
                numbaskets(int): expected number of colors to assign. This value
                              will not be useful is isuniq = True, and may become
                              less due to the hardness to assign quantile colors.
                isuniq (bool): if isuniq = False, assign map quantile colors.
                               Otherwise, assign color with unique values. 
    """
    if (numbaskets < 2):
        print "Error: number of baskets is less than 2."
        exit(1)
    quantilelist, isuniq = getQuantileList("./Data/%s.txt" % filename, numbaskets, nomin, nomax, isuniq)
    if isuniq:
        numbaskets = len(quantilelist)
        classColorCondlist = []
        rgblist = getRGBList(numbaskets)
        for tick, rgb in zip(quantilelist, rgblist):
            condstr = "[pixel] == %s" % str(tick)
            classColorCondlist.append((tick, condstr, rgb))
        print classColorCondlist
        return classColorCondlist

    numbaskets = len(quantilelist) + 1   # note that the fisrt cond == quantilelist[0]
    rgblist = getRGBList(numbaskets)
    lastindex = numbaskets-1

    classColorCondlist = []
    if (numbaskets > 1):
        condstr = "[pixel] == "+str(quantilelist[0]) 
        classColorCondlist.append((str(0), condstr, rgblist[0]))
    for i in xrange(1, lastindex):  #note that the last index is numbaskets
        condstr = "([pixel] > " + str(quantilelist[i-1]) + \
                  ") && ([pixel] <= " + str(quantilelist[i]) + ")"
        classColorCondlist.append((str(i), condstr, rgblist[i]))
    condstr = "[pixel] > "+str(quantilelist[lastindex-1]) 
    classColorCondlist.append((str(lastindex), condstr, rgblist[lastindex]))
    print classColorCondlist
    return classColorCondlist

def main():
    filename = sys.argv[1]
    numbaskets = int(sys.argv[2])
    if (numbaskets < 2):
        print "Error: number of baskets is less than 2."
        exit(1)
    classColorCondlist = genclassColorCondlist_results(filename, numbaskets, nomin=True)
    genSimMap_results("26916", classColorCondlist, filename)

    # print getRGBList(5)

    # genSimMap("26916", [("0",  "[pixel] == 0","0 77 168"),
    #                       ("1",  "([pixel] >     0) && ([pixel]<=   100)"," 46  70 255"),
    #                       ("2",  "([pixel] >   100) && ([pixel]<=   300)"," 56 116 255"),
    #                       ("3",  "([pixel] >   300) && ([pixel]<=   500)"," 56 169 255"),
    #                       ("4",  "([pixel] >   500) && ([pixel]<=  1000)"," 41 219 255"),
    #                       ("5",  "([pixel] >  1000) && ([pixel]<=  2000)"," 64 255 239"),
    #                       ("6",  "([pixel] >  2000) && ([pixel]<=  3000)","138 255 190"),
    #                       ("7",  "([pixel] >  3000) && ([pixel]<=  5000)","182 255 143"),
    #                       ("8",  "([pixel] >  5000) && ([pixel]<=  8000)","218 255  97"),
    #                       ("9",  "([pixel] >  8000) && ([pixel]<= 10000)","248 255  38"),
    #                       ("10", "([pixel] > 10000) && ([pixel]<= 15000)","255 255   0"),
    #                       ("11", "([pixel] > 15000) && ([pixel]<= 20000)","255 179   0"),
    #                       ("12", "([pixel] > 20000) && ([pixel]<= 25000)","255 132   0"),
    #                       ("13", "([pixel] > 25000) && ([pixel]<= 50000)","255  81   0"),
    #                       ("14", " [pixel]>  50000                      ","255   0   0"),
    #                       ], "pop_grav_attr")

if __name__ == '__main__':
    if (len(sys.argv) < 2):
        print "Require Arg1: the mapfile name without postfix.\n" + \
              "        Arg2: the number of quantile baskets."
        exit(1)
    main()
