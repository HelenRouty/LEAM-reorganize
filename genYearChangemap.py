# After we get probability map for each cell where each cell
# has a probability for people to move in from 0 to 1, we 
# roll a dice for each year. 
# We first caculate how much population increase for each year
# using a linear function. When we get the total population
# increment for the entire study region, we roll a dice and
# give one cell the number of people that this cell's density
# indicate of. Then, we roll another dice and another until
# all the population increment has been used up by the cells
# choicen using rolling dice.

# Note that we can only change the non-residential and non-commercial
# cells (except re-developement cells that only allows residential
# been converted to commercial but not the reverse). Once a cell
# has been changed to commercial or residential, on the year of
# change map, this cell is given the year.
# In the final year change map, the color changes with the year change.
import sys, os
from leamsite import LEAMsite
from StringIO import StringIO
import csv

resultsdir = 'http://portal.leam.illinois.edu/chicago/luc/scenarios/test4_scenario'

def grassConfig(location='grass', mapset='model',
    gisbase='/usr/local/grass-6.4.5svn', gisdbase='.'):
    """ Set grass environment to run grass.script as grass
    """
    os.environ['GISBASE'] = gisbase
    os.environ['GRASS_VERBOSE'] = '0'
    os.environ['GRASS_OVERWRITE'] = '1'
    sys.path.append(os.path.join(gisbase, 'etc', 'python'))

    global grass
    __import__('grass.script')
    grass = sys.modules['grass.script']
    from grass.script.setup import init
    gisrc = init(gisbase, gisdbase, location, mapset)   

def getDemandYearPop(demandstr, demandname):
    """@input: demandstr: StringIO gotten by getURL from leamsite.
               demandname is 'Population' or 'Employment'.
       @output: [(startyear, startpop), (endyear, endpop)]
    """
    demandstrs = demandstr.strip().split('\n')
    for i in xrange(len(demandstrs)):
        if demandstrs[i].startswith(demandname):
            startyear, startpop = demandstrs[i+1].strip().split(',')
            endyear, endpop = demandstrs[i+2].strip().split(',')
            break

    return int(startyear.strip()), int(endyear.strip()),  \
           int(startpop.strip()),  int(endpop.strip())

def interpolate(x1, x2, y1, y2):
    """Linearly interpolate the range(x1, y1) to (x2, y2).
       So that for each interval 1 of x, there there is a
       y corresponding to it.
       require: y1 >= y2, x1 >= x2
       @output: results: an ascending list of (x, y) 
    """
    results = []
    delta = float(y2-y1)/float(x2-x1)
    for i in xrange(0,x2-x1):
        results.append((x1+i, int(round(y1+i*delta, 0))))
    results.append((x2,y2))
    return results

def yearchange(yearpoplist):
    grassConfig()
    # how this have been done? where percell maps come from?
    # --regional: subregional: processProjections...
    # input = '%s,%s' % (time, year)? where it comes from?
    grass.mapcalc('int1=int($mult*$percell)', percell='ppcell',
                  mult=10000.0, quiet=True)
    stats = grass.read_command('r.stats', flags='c', quiet=True,
                               input='int1')
    print stats
    for l in stats.splitlines():
        # not valid...
        t,val,count = l.split()
        print t, " ", val, " ", count
        ts[int(t)]=ts.get(int(t),0.0)+int(val)*int(count)/mult
        print t[int(t)]

def main():
    # global site
    # site = LEAMsite(resultsdir, user=sys.argv[1], passwd=sys.argv[2])
    # demandurl = "http://portal.leam.illinois.edu/chicago/luc/projections/test2_projection/getGraph"
    # demandstr = site.getURL(demandurl).getvalue() # the demand is of type StringIO
    
    # yr1, yr2, pop1, pop2 = getDemandYearPop(demandstr, 'Population')
    # yearpoplist = interpolate(yr1, yr2, pop1, pop2)
    # print yearpoplist

    yearchange([])




if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Require Arg1: username, Arg2: password to connect to plone site."
        exit(1)
    main()
