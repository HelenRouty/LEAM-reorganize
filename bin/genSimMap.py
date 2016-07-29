import sys
sys.path += ['..']
import pandas as pd
import numpy as np
from sets import Set

SIMMAPHEADER = "./Inputs/simMapheader.txt"

def genSimMap(spatialcode, classColorCondlist, filename):
    """This function generates simMap: the meta data for maps projected on google map
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

def getQuantileList(mapfilename, numbaskets):
    if (numbaskets < 2):
        print "Error: number of baskets is less than 2."
        exit(1)
    df = pd.read_csv(mapfilename, sep=r"\s+", skiprows=6, header=None)
    arr = df.values.flatten()
    arrlen = len(arr)
    basketsize = arrlen/numbaskets
    sortedarr = np.sort(arr)
    arrticks = sortedarr[0:arrlen-1:basketsize]
    print basketsize
    print arrticks
    # if the maximum or the base values are too much, remove them.
    # TODO: this is a brute force solution. Varies maps may have different
    # cases. Should be improved to cater all map cases.
    if len(arrticks) > 3                                and \
       arrticks[-1] == arrticks[-2] and \
       arrticks[-2] == arrticks[-3] and \
       arrticks[-3] == arrticks[-4]:
       sortedarr = sortedarr[sortedarr!=arrticks[-1]]
       arrticks = sortedarr[0:len(sortedarr)-1:len(sortedarr)/numbaskets]
       print arrticks,  " after remove the maximum"
    if len(arrticks) > 3          and \
       arrticks[0] == arrticks[1] and \
       arrticks[1] == arrticks[2] and \
       arrticks[2] == arrticks[3]:
       sortedarr = sortedarr[sortedarr!=arrticks[0]]
       arrticks = sortedarr[0:len(sortedarr)-1:len(sortedarr)/numbaskets]
       print arrticks, " after remove the base"

    # multiplier = 1
    # while(arrticks[-1]*multiplier < numbaskets):
    #     multiplier *= 10
    # if multiplier != 1:
    #     arrticks = [tick * multiplier for tick in arrticks]

    retarr = []
    retarr.append(arrticks[0])
    for i in xrange(1, numbaskets):
        if arrticks[i] != arrticks[i-1]:
            # retarr.append(int(arrticks[i]))
            retarr.append(arrticks[i])

    return retarr, len(retarr)

def getRGBList(numbaskets):
    rgblist = []
    #red and green from 50 to 255 to make more distinguishment.
    
    # Red Color Code List
    rnum50 = rnum255 = max(0, numbaskets/3-1)
    rarr = np.linspace(50, 255, numbaskets-rnum50-rnum255, dtype=np.int)
    rlist = [50]*rnum50 + rarr.tolist() + [255]*rnum255

    # Green Color Code List
    gnum255 = numbaskets/3
    lengarr = numbaskets-gnum255
    garr1 = np.linspace(50, 255, lengarr/2, dtype=np.int)
    garr2 = np.linspace(255, 50, lengarr-lengarr/2, dtype=np.int)
    glist = garr1.tolist() + [255]*gnum255 + garr2.tolist()

    # Blue Color Code List
    bnum0 = bnum255 = max(0, numbaskets/3-1)
    barr = np.linspace(255, 0, numbaskets-bnum0-bnum255, dtype=np.int)
    blist = [255]*bnum255 + barr.tolist() + [0]*bnum0

    for i in xrange(numbaskets):
        rgblist.append(str(rlist[i]) + " " + str(glist[i]) + " " + str(blist[i]))
    return rgblist

def genclassColorCondlist(filename, numbaskets):
    if (numbaskets < 2):
        print "Error: number of baskets is less than 2."
        exit(1)

    quantilelist, numbaskets =  getQuantileList("./Data/" + filename + ".txt", numbaskets)
    numbaskets += 1   # note that the fisrt cond == quantilelist[0]
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
    classColorCondlist = genclassColorCondlist(filename, numbaskets)
    genSimMap("26916", classColorCondlist, filename)

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