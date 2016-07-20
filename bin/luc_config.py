import os, sys
from operator import itemgetter
from xml.etree.ElementTree import fromstring

from leamsite import LEAMsite


class LUC:
    """utility class that provide support for parsing a LUC config file"""

    def __init__(self, configfile):
        """parses config file"""
        self.scenario = {}
        self.projection = {}
        self.drivers = {}
        self.centers = {}
        self.nogrowth_maps = {}
        self.probmapcacheurl = ""

        f = open(configfile)
        root = fromstring(f.read())
 
        if root.tag != 'model':
            print "The configuration does not have model tag, return."
            return

        for s in root.find('scenario').getchildren():
            if s.tag == 'probmap':
                for i in s.getchildren():
                    if i.tag == 'centers':
                        for center in i.getchildren():
                            self.centers[center.tag] = center.text
                    elif i.tag == 'nogrowth_maps':
                        for ngmap in i.getchildren():
                            self.nogrowth_maps[ngmap.tag] = ngmap.text
                    elif i.tag == "probmapcache":
                        self.probmapcacheurl = i.text 
                    else:
                        self.drivers[i.tag] = i.text
            elif s.tag == 'projection':
                for i in s.getchildren():
                    self.projection[i.tag] = i.text
            else:
                self.scenario[s.tag] = s.text

        f.close()
        self._config_sanity_check()

    def _config_sanity_check(self):
        if not ("id" and "title" and "results" and "grass_loc" )in self.scenario:
            print "Error: Config file requires scenario id, title, results, and grass_loc."
            exit(1)
        if not ("id" and "title" and "year" and "url" and "roads" and "landuse" ) in self.drivers:
            print "Error: Config file requires probmap id, title, year, url, roads, and landuse."
            exit(1)
        if not ("id" and "title" and "startyear" and "endyear" and 
            "demandlist" and "boundary" and "pop_density" and "emp_density") in self.projection:
            print "Error: Config file requires projection id, title, startyear, endyear,\
             demandlist, boundary, pop_density, and emp_density."
            exit(1)

def main():
    luc = LUC('config.xml')
    print "scenario:\n", luc.scenario
    print "drivers:\n", luc.drivers
    print "projection:\n", luc.projection
    print "centers:\n", luc.centers
    print "nogrowth_maps:\n", luc.nogrowth_maps
    print "probmapcache: \n", luc.probmapcacheurl
    
if __name__ == '__main__':
    main()
