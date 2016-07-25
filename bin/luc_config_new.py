import os, sys
from operator import itemgetter
from xml.etree.ElementTree import fromstring

from leamsite import LEAMsite


class LUC:
    """utility class that provide support for parsing a LUC config file"""

    def __init__(self, configfile, mode):
        """parses config file: mode is growth or decline
        scenario
            id
            title
            results
            grass_loc
            projections
                projection1
                    id
                    title
                    startyear
                    endyear
                    graph   (year and corresponding demand list)
                    layer   (boundary)
                    pop_density
                    emp_density
                projection2
                ...

            probmaps
                id
                title
                year
                download (probmapcacheurl)
                tdm      (transport demand model)
                probmap1
                    download
                    nogrowth_maps
                        nogrowth_map1
                        nogrowth_map2
                    empcenters
                        empcenter1
                        empcenter2
                    popcenters
                        popcenter1
                        popcenter2
                probmap2
                    ...
        """
        self.scenario = {}
        self.ismodeexist = True
        self.projections = {} # a dictionary of projection dictionaries
        self.drivers = {} # a dictionary of drivers
        self.nogrowthmaps = {}
        self.empcenters = {}
        self.popcenters = {}

        f = open(configfile)
        root = fromstring(f.read())
 
        if root.tag != 'model':
            print "The configuration does not have model tag, return."
            return

        for s in root.find('scenario').getchildren():
            if s.tag == mode:
                for projection in s.getchildren():
                    projection_dict = {}
                    for i in projection:
                        projection_dict[i.tag] = i.text
                    self.projections[projection.tag] = projection_dict
            elif s.tag == mode+'map':
                for driver in s.getchildren():
                    driver_dict = {}
                    for i in driver:  
                        if i.tag == 'nogrowth_maps':
                            for ngmap in i.getchildren():
                                self.nogrowthmaps[ngmap.tag] = ngmap.text
                        elif i.tag == 'empcenters':
                            for empcenter in i.getchildren():
                                self.empcenters[empcenter.tag] = empcenter.text
                        elif i.tag == 'popcenters':
                            for popcenter in i.getchildren():
                                self.popcenters[popcenter.tag] = popcenter.text
                        else:
                            driver_dict[i.tag] = i.text
                    self.drivers[driver.tag] = driver_dict
            else:
                self.scenario[s.tag] = s.text

        f.close()
        self._check_mode(mode)
        if self.ismodeexist:
            self._config_sanity_check()

    def _check_mode(self, mode):
        if not any(self.drivers and self.projections):
            self.ismodeexist = False

    def _config_sanity_check(self):
        if not ("id" and "title" and "results" and "grass_loc" )in self.scenario:
            print "Error: Config file requires scenario id, title, results, and grass_loc."
            exit(1)
        if not ("id" and "title" and "year" and "url" and "tdm" and "landuse") in self.drivers['probmap']:
            print "Error: Config file requires probmap id, title, year, url, roads, landuse"
            exit(1)
        if not ("id" and "title" and "startyear" and "endyear" and 
            "demandlist" and "boundary" and "pop_density" and "emp_density") in self.projections['projection']:
            print "Error: Config file requires projection id, title, startyear, endyear, ",
            "demandlist, boundary, pop_density, and emp_density."
            exit(1)
        if not (any(self.nogrowthmaps) and
                any(self.empcenters) and
                any(self.popcenters)):
            print "Error: Config file requires nogrowth map, empcenters and popcenters"
            exit(1)

def main():
    luc_growth = LUC('config.xml', 'decline')
    if not luc_growth.ismodeexist:
        return
    print "scenario:\n", luc_growth.scenario
    print "drivers:\n", luc_growth.drivers
    print "projection:\n", luc_growth.projections
    print "emp centers:\n", luc_growth.empcenters
    print "pop centers: \n", luc_growth.popcenters
    print "nogrowth_maps:\n", luc_growth.nogrowthmaps
    
if __name__ == '__main__':
    main()
