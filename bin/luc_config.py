import os, sys
from operator import itemgetter
from xml.etree.ElementTree import fromstring

from leamsite import LEAMsite


class LUC:
    """utility class that provide support for parsing a LUC config file"""

    def _get_dict(self, tree):
        """Import the XML fragment as a dict.  Assumes the XML fragment
           is flat.  Children with other children will  be skipped.
           @param tree points to Etree Element
           @retuns dictionary
        """
        d = {}
        for e in tree.getchildren():
            d[e.tag] = e.text
        return d

    def _get_list(self, tree):
        """Import the XML fragment as a dict.  Assumes the XML fragment
           is flat.  Children with other children will  be skipped.
           @param tree points to Etree Element
           @retuns list
        """
        l = []
        for e in tree.getchildren():
            l.append(e.text)
        return l

    def _get_drivers(self, tree):
        d = {}
        for e in tree.getchildren():
            if e.tag == 'nogrowth_maps':
                d['nogrowth'] = self._get_list(e)
            elif e.tag == 'empcenters':
                d['empcenters'] = self._get_dict(e)
            elif e.tag == 'popcenters':
                d['popcenters'] = self._get_dict(e)
            else:
                d[e.tag] = e.text
        return d


    def __init__(self, configfile):
        """parses config file"""
        self.scenario = {}
        self.growth = []
        self.growthmap = []
        self.decline = []
        self.declinemap = []

        try:
            with open(configfile) as f:
                config = f.read()
        except IOError:
            raise
            
        tree = fromstring(config)

        # make sure this 
        if tree.tag != 'model':
            return

        for s in tree.find('scenario').getchildren():
            if s.tag == 'growth':
                for i in s.getchildren():
                    self.growth.append(self._get_dict(i))
            elif s.tag == 'growthmap':
                for i in s.getchildren():
                    self.growthmap.append(self._get_drivers(i))
            elif s.tag == 'decline':
                for i in s.getchildren():
                    self.decline.append(self._get_dict(i))
            elif s.tag == 'declinemap':
                for i in s.getchildren():
                    self.declinemap.append(self._get_drivers(i))
            else:
                self.scenario[s.tag] = s.text

            self.growthmap = sorted(self.growthmap, key=itemgetter('year'))
            self.declinemap = sorted(self.declinemap, key=itemgetter('year'))


def main():
    f = open(sys.argv[1])
    luc = LUC(f.read())
    f.close()

    site = LEAMsite('http://ewg.leamgroup.com')
    base = luc.growth[0]['id']
    print luc.growth[0]['layer']
    site.getURL(luc.growth[0]['layer'], filename=base+'.layer.zip')
    site.getURL(luc.growth[0]['graph'], filename=base+'.graph')

    print "SCENARIO:", luc.scenario.keys()
    print "GROWTH[0]:", luc.growth[0].keys()
    print "GROWTH[0] GRAPH:", luc.growth[0]['graph']
    print "GROWTHMAPS: len =", len(luc.growthmap)
    print "GROWTHMAPS:", luc.growthmap[0].keys()
    print "GROWTHMAPS nogrowth:", luc.growthmap[0]['nogrowth']
    print "GROWTHMAPS: download=", luc.growthmap[0]['download']
    print "DECLINE: len=", len(luc.decline),
    print "DECLINE: len=", len(luc.declinemap),

if __name__ == '__main__':
    main()
