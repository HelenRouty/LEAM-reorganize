"""This file does tests on the functions of 
   original leam code: leamsite.py
"""
import sys, os
import re
import urllib2
import os.path as path
from StringIO import StringIO
from mechanize import Browser
from optparse import OptionParser

from leamsite import LEAMsite

resultsdir = 'http://portal.leam.illinois.edu/chicago/luc/scenarios/test4_scenario'
url = 'http://portal.leam.illinois.edu/chicago/luc/testfolder'

def main():
	# conection to the portal 
    global site
    site = LEAMsite(resultsdir, user=sys.argv[1], passwd=sys.argv[2])
    
    print "--upload pop_attr map..."
    popattr_simmap  = 'Data/pop_att.gtif'
    popattr_mapfile = 'Outputs/pop_att.map'
    popattrurl = site.putSimMap("popattr.tif", "popattr.map", url,
        simmap_file=open(popattr_simmap, 'rb'), 
        mapfile_file=open(popattr_mapfile, 'rb'))
    site.updateSimMap(popattrurl, title='popattr-autoColor', 
        description='interpolated attractionmap for population centers.\n \
                     Automatic Color works only for integer quantile values.')
    # # print "--download img..."
    # # site.saveFile(url+"/clover.jpg", dir="Download")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Require Arg1: username, Arg2: password to connect to plone site."
        exit(1)
    main()
