"""
This script will do:
1. (optional)-overlap the miniumum of 100 travelcost maps to have a complete travelcost map. ./Data/travelcost-pop.txt
2. read the interpolated attrmap and the travelcost map into an array seperately, and create a dictionary to map them. Sort.
3. use the two arrays and matplotlib libarary and ggplot2 to generate:
   (1) travelcost vs. attractiveness graph
   (2) travelcost vs. low&high residential frequency (type 21, 22)
   (3) travelcost vs. low&high commercial frequency (type 23, 24)
   (4) attractiveness vs. low&high residentail frequency 
   (5) attractivenss vs. low&high commercial frequency

"""

#from ggplot import * #ggplot is best to be used with pandas DataFrames
import sys
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from optparse import OptionParser
from Utils import createdirectorynotexist, extractheader, outfilename
import time 

if (len(sys.argv) < 3):
    print "Error: You need to specify at least two arguments: #attrmap baskets and #costmap baskets."
    exit(1)


LANDROADCLASSMAP = "./Data/landroadclassmap.txt"
RESIDENTIALMIN = 21
RESIDENTIALMAX = 22
COMMERCIALMIN  = 23
COMMERCIALMAX  = 24
ROADCLASSMAX   = 6
ATTRBASKETNUM = int(sys.argv[1])
COSTBASKETNUM = int(sys.argv[1])
ATTRBASE = 434 ### needs to be set to the smallest value in attrmap
COSTMAX = 999  ### needs to be set to the default value in costmap
COSTBASE = 0
RES = "Residential"
COM = "Commercial"
ATT = "Attractiveness"
CST = "Travelcost"

# for gettravelcostmap
ISEMP = 1
if ISEMP == 1:
    CENTERLIST = "./Data/empcenterlist.txt"
    ATTRMAP = "./Data/emp_grav_attr.txt"
    TRCOSTMAP = "./Data/emp_cost.txt"
    ATTRFREQ_COM = "./Data/analysis/emp/attrfreq-commericial.png"
    ATTRFREQ_RES = "./Data/analysis/emp/attrfreq-residential.png"
    COSTFREQ_COM = "./Data/analysis/emp/trcostfreq-commercial.png"
    COSTFREQ_RES = "./Data/analysis/emp/trcostfreq-residential.png"
    ATTRBASE = 434
else:
    CENTERLIST = "./Data/popcenterlist.txt"
    ATTRMAP = "./Data/pop_grav_attr.txt"
    TRCOSTMAP = "./Data/pop_cost.txt"
    ATTRFREQ_COM = "./Data/analysis/pop/attrfreq-commericial.png"
    ATTRFREQ_RES = "./Data/analysis/pop/attrfreq-residential.png"
    COSTFREQ_COM = "./Data/analysis/pop/trcostfreq-commercial.png"
    COSTFREQ_RES = "./Data/analysis/pop/trcostfreq-residential.png"
    ATTRBASE = 3742
HEADER = "./Input/arcGISheader.txt"


def to_percent(y, position):
    """[reference:http://matplotlib.org/examples/pylab_examples/histogram_percent_demo.html]
    """
    s = str(100 * y)

    # The percent symbol needs escaping in latex
    if matplotlib.rcParams['text.usetex'] is True:
        return s + r'$\%$'
    else:
        return s + '%'

def plotgraph(x, y, xsize, outfile, name, mapname):
    plt.close("all")
    fig, ax = plt.subplots()
    # set the grids of the x axis
    if mapname == ATT:
        major_ticks = xrange(0, x[-1]+1000, 1000)
        minor_ticks = xrange(0, x[-1]+1000, 100)
    else:
        major_ticks = xrange(0, x[-2]+10, 10)
        minor_ticks = xrange(0, x[-2]+10, 1)
    ax.set_xticks(major_ticks)
    ax.set_xticks(minor_ticks, minor=True)
    ax.grid(which='minor', alpha=0.2)
    ax.grid(which='major', alpha=0.5)

    # set the range of the y axis
    plt.ylim(0, 1)
    # set the title and labels
    plt.title(name +' ' + mapname + ' Frequency Distribution')
    plt.xlabel(mapname + ' Score')
    plt.ylabel('Fraction ' + name + ' Over All Landuse Type ' + mapname +' Frequency')
    # set the y axis values to be 100% times.
    formatter = FuncFormatter(to_percent)
    plt.gca().yaxis.set_major_formatter(formatter)

    #plot the graph and pinpoint the max y value point
    plt.plot(x, y, 'ro--')
    ymax_index = np.argmax(y)
    ymax       = y[ymax_index]
    ymax_xval  = x[ymax_index]
    plt.scatter(ymax_xval, ymax*100)
    plt.grid(True)

    # save the figure to file
    plt.savefig(outfile)

def frequencyanalysis_attr(attr_res_arr, attr_arr, attr_arr_x, attrbasketsize_1st, RESCOM, ATTRFREQ, 
                                             ATT=ATT, ATTRBASKETNUM=ATTRBASKETNUM, ATTRBASE=ATTRBASE):
    attr_res_arr_nobase     = attr_res_arr[attr_res_arr > ATTRBASE]
    print "NUM " + RESCOM + " CELLS CONSIDERED: ", len(attr_res_arr_nobase) 
    attr_res_arr_nbsort     = np.sort(attr_res_arr_nobase)
    attr_res_basketsize_1st = len(attr_res_arr[attr_res_arr == ATTRBASE])
    attr_res_freq = [attr_res_basketsize_1st]
    attr_arr_freq = [attrbasketsize_1st]
    cur1 = attr_arr_x[1]
    for i in xrange(2, ATTRBASKETNUM+1): #i is for cur2. in total ATTRBASKETNUM baskets.
        cur2 = attr_arr_x[i]
        mask = (attr_res_arr >= cur1) & (attr_res_arr < cur2)
        attr_res_freq = np.append(attr_res_freq, len(attr_res_arr[mask]))
        mask = (attr_arr >= cur1) & (attr_arr < cur2)
        attr_arr_freq = np.append(attr_arr_freq, len(attr_arr[mask]))
        cur1 = cur2
    attr_res_freq = np.append(attr_res_freq, len(attr_res_arr[attr_res_arr >= cur1]))
    attr_arr_freq = np.append(attr_arr_freq, len(attr_arr[attr_arr >= cur1]))
    

    print "---------------------attr_"+RESCOM.lower()+"_freq----------------\n",attr_res_freq.astype(np.int)
    print "---------------------attr_arr_freq----------------\n",attr_arr_freq.astype(np.int)
    attr_res_y = np.divide(attr_res_freq*1.0, attr_arr_freq)
    attr_res_y = np.nan_to_num(attr_res_y)
    print "---------------------attr_"+RESCOM.lower()+"_y----------------\n",attr_res_y
    outgraphfname = ATTRFREQ[:-4]+"-"+str(ATTRBASKETNUM)+".png"
    outdatafname = ATTRFREQ[:-4]+"-"+str(ATTRBASKETNUM)+".csv"
    createdirectorynotexist(outgraphfname)
    plotgraph(attr_arr_x, attr_res_y, ATTRBASKETNUM, outgraphfname, RESCOM, ATT)
    outdata_arr = np.asarray([attr_arr_x, attr_res_freq, attr_arr_freq, attr_res_y])
    outdata_arr = np.transpose(outdata_arr)
    np.savetxt(outdatafname, outdata_arr,fmt='%5.5f',delimiter=',',
                                         header="x,res/com,original,y", comments='')

def frequencyanalysis_cost(cost_res_arr, cost_arr, cost_arr_x, RESCOM, COSTFREQ, 
                           CST=CST, COSTBASKETNUM=COSTBASKETNUM, COSTMAX=COSTMAX, COSTBASE=COSTBASE):
    cost_res_arr_nobase      = cost_res_arr[(cost_res_arr < COSTMAX)&(cost_res_arr > COSTBASE)]
    print "NUM " + RESCOM + " CELLS CONSIDERED: ", len(cost_res_arr_nobase)
    cost_res_arr_nbsort      = np.sort(cost_res_arr_nobase)
    cost_res_basketsize_last = len(cost_res_arr[cost_res_arr == COSTMAX])
    cost_res_freq = []
    cost_arr_freq = []
    cur1 = cost_arr_x[0]
    xlen = len(cost_arr_x)
    for i in xrange(1, xlen): #i is for cur2. in total ATTRBASKETNUM baskets.
        cur2 = cost_arr_x[i]
        mask = (cost_res_arr >= cur1) & (cost_res_arr < cur2)
        cost_res_freq = np.append(cost_res_freq, len(cost_res_arr[mask]))
        mask = (cost_arr >= cur1) & (cost_arr < cur2)
        cost_arr_freq = np.append(cost_arr_freq, len(cost_arr[mask]))
        cur1 = cur2
    mask = (cost_res_arr >= cur1) & (cost_res_arr < COSTMAX)
    cost_res_freq = np.append(cost_res_freq, len(cost_res_arr[mask]))
    mask = (cost_arr >= cur1) & (cost_arr < COSTMAX)
    cost_arr_freq = np.append(cost_arr_freq, len(cost_arr[mask]))
    #cost_res_freq = np.append(cost_res_freq, cost_res_basketsize_last)
    #cost_arr_freq = np.append(cost_arr_freq, costbasketsize_last)


    print "---------------------cost_"+RESCOM.lower()+"_freq----------------\n",cost_res_freq.astype(np.int)
    print "---------------------cost_arr_freq----------------\n",cost_arr_freq.astype(np.int)
    cost_res_y = np.divide(cost_res_freq, cost_arr_freq)
    cost_res_y = np.nan_to_num(cost_res_y)
    cost_res_y[cost_res_y > 100] = 100
    print "---------------------cost_"+RESCOM.lower()+"_y----------------\n",cost_res_y
    outgraphfname = COSTFREQ[:-4]+"-"+str(COSTBASKETNUM)+".png"
    outdatafname = COSTFREQ[:-4]+"-"+str(COSTBASKETNUM)+".csv"
    createdirectorynotexist(outgraphfname)
    plotgraph(cost_arr_x, cost_res_y, COSTBASKETNUM, outgraphfname, RESCOM, CST)
    print outdatafname
    outdata_arr = np.asarray([cost_arr_x, cost_res_freq, cost_arr_freq, cost_res_y])
    outdata_arr = np.transpose(outdata_arr)
    np.savetxt(outdatafname, outdata_arr, fmt='%5.5f',delimiter=',', 
                                          header="x,res/com,original,y", comments='')



def main():
    landroadclassmap = pd.read_csv(LANDROADCLASSMAP, sep=r"\s+", skiprows=6, header=None)
    attrmap          = pd.read_csv(ATTRMAP, sep=r"\s+", skiprows=6, header=None)
    attrmap          = attrmap.round().astype(np.int)
    travelcostmap    = pd.read_csv(TRCOSTMAP, sep=r"\s+", skiprows=6, header=None)
    travelcostmap    = travelcostmap.round().astype(np.int)
    

    plt.hist(attrmap.values.flatten())
    plt.savefig("histogram.png")
    exit(1)

    landroad_arr   = landroadclassmap.values.flatten()
    mask_noroad    = (landroad_arr > ROADCLASSMAX)
    mask_res       = (landroad_arr > ROADCLASSMAX) & (landroad_arr >= RESIDENTIALMIN)& (landroad_arr <= RESIDENTIALMAX)
    mask_com       = (landroad_arr > ROADCLASSMAX) & (landroad_arr >= COMMERCIALMIN) & (landroad_arr <= COMMERCIALMAX)
 
    attr_arr_org   = attrmap.values.flatten()
    attr_arr       = attr_arr_org[mask_noroad]
    attr_res_arr   = attr_arr_org[mask_res]
    attr_com_arr   = attr_arr_org[mask_com]
    cost_arr_org   = travelcostmap.values.flatten()
    cost_arr       = cost_arr_org[mask_noroad]
    cost_res_arr   = cost_arr_org[mask_res]
    cost_com_arr   = cost_arr_org[mask_com]


    # find one x axis (quantile or equal interval) for attr_arr, attr_res_arr, attr_com_arr
    # note that, about 63.5% attrmap cells have base value, so we do not consider base value cells
    # when finding x axis for quantile. We will set attrbase as the first x tick.
    attr_arr_nobase    = attr_arr[attr_arr > ATTRBASE]
    print "NUM CELLS CONSIDERED: ", len(attr_arr_nobase) 
    attr_arr_nblen     = len(attr_arr_nobase)
    attrbasketsize     = attr_arr_nblen/ATTRBASKETNUM
    attr_arr_nbsort    = np.sort(attr_arr_nobase)
    attr_arr_x         = attr_arr_nbsort[0:attr_arr_nblen-1:attrbasketsize] # the x axis tick values 
    attr_arr_x         = np.concatenate(([ATTRBASE], attr_arr_x.tolist()))  # need add one basket for base value
    attr_arr_x         = attr_arr_x[0:ATTRBASKETNUM+1]                      # merge the last basket to the previous one
    print "---------------------attr_arr_x----------------\n", attr_arr_x
    attrbasketsize_1st = len(attr_arr[attr_arr == ATTRBASE])

    frequencyanalysis_attr(attr_res_arr, attr_arr, attr_arr_x, attrbasketsize_1st, RES, ATTRFREQ_RES)
    frequencyanalysis_attr(attr_com_arr, attr_arr, attr_arr_x, attrbasketsize_1st, COM, ATTRFREQ_COM)

    # find one x axis (quantile or equal interval) for attr_arr, attr_res_arr, attr_com_arr
    # note that, about 63.5% attrmap cells have base value, so we do not consider base value cells
    # when finding x axis for quantile. We will set attrbase as the first x tick.
    cost_arr_nobase    = cost_arr[(cost_arr < COSTMAX)&(cost_arr > COSTBASE)]
    print "NUM CELLS CONSIDERED: ", len(cost_arr_nobase)
    cost_arr_nblen     = len(cost_arr_nobase)
    costbasketsize     = cost_arr_nblen/COSTBASKETNUM
    cost_arr_nbsort    = np.sort(cost_arr_nobase)
    cost_arr_x         = cost_arr_nbsort[COSTBASE+1:cost_arr_nblen-1:costbasketsize] # the x axis tick values 
    cost_arr_x         = cost_arr_x[:-1]                                    # merge the last basket to the previous one
    cost_arr_x         = np.insert(cost_arr_x, 0, COSTBASE)
    cost_arr_x         = np.unique(cost_arr_x)
   # cost_arr_x         = 
    #cost_arr_x         = np.append(cost_arr_x, COSTMAX)
    print "---------------------cost_arr_x----------------\n",cost_arr_x
    
    #costbasketsize_last= len(cost_arr[cost_arr == COSTMAX])
    #costbasketsize_rest= cost_arr_nblen%COSTBASKETNUM
    #costbasketsize_nths= np.full((1, COSTBASKETNUM), costbasketsize,dtype=np.int)

    frequencyanalysis_cost(cost_res_arr, cost_arr, cost_arr_x, RES, COSTFREQ_RES)
    frequencyanalysis_cost(cost_com_arr, cost_arr, cost_arr_x, COM, COSTFREQ_COM)

if __name__ == "__main__":
    main()
    
