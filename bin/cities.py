#!/usr/bin/env python
"""
The following script is piped through a shell to perform
necessary grass calculations.

Requires the following arguments (all strings):
cities -- name of the cities raster layer.  Each city is identified by
          by the cat number in the associated cities vector layer.
id     -- id (cat) of the city
output -- the output layer name
"""
import sys,os
from optparse import OptionParser
sys.path += ['./bin']
from glob import iglob
import time
from sets import Set

usage = "usage: %prog [options] <cities>"

description = """ Iterates through each city in the <cities> 
vector layer computing a city attractor map.  Each city attractor 
map is aggregated into the final <attmap> to create a cities gravity 
map using POP/(cityatt+1)^2.
"""

def normalize(layer, result=""):
    "normalize a composity gravity map"
    if (result==""):
        result=layer+"_norm"

    for l in os.popen('r.univar %s' % layer):
        print l
        if l.startswith('maximum:'):
            break

    s, max = l.strip().split()
    os.system('r.mapcalc %s=%s/%s' % (result,layer,max))


def grass_config(location, mapset, gisbase='/usr/local/grass-6.4.5svn', gisdbase='.'):
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


def make_city_tt(cities, cat, overland='overlandTravelTime30', 
                 interstates='intTravelTime30', xover='cross', maxcost='180'):
    """Extracts a specific city, buffers it, and then uses r.multicost
       to determine travel time out to maxcost (minutes), and computes
       attractor maps based on pop/tt^2.
       @inputs: cities (vector map) : center attractors
                cat (int) : the class value of the centers
       @outputs: travelcost (str) : the name of the class travelcost map

       Note: ywkim added, it originally extracts from the raster
       but it is not accurate if there are many points overlapped
       so change this to work using vector first then convert to raster
    """
    classlayer = '%s%s'%(cities,cat)
    travelcost = '%s_travelcost' % classlayer
    grass.run_command('v.extract', input=cities, output=classlayer,
        where="class = %s" % (cat), overwrite=True, quiet=True)
    grass.run_command('g.region', res=30)
    grass.run_command('v.to.rast', input=classlayer, output=classlayer, 
        use='val', value=1, overwrite=True)
    grass.run_command('g.remove', vect=classlayer)
    grass.run_command('r.buffer', input=classlayer, output=classlayer, dist='180')
    grass.mapcalc('%s=if(%s)' % (classlayer, classlayer))
    grass.run_command('r.multicost', input=overland, m2=interstates, 
        xover=xover, start_rast=classlayer, output=travelcost, max_cost=maxcost)
    grass.run_command('g.remove', rast=classlayer)
    #grass.run_command('r.out.gdal', input=travelcost, 
    #   output='./Data/'+travelcost+".tif", type='Float64')
    return travelcost


def parse_args():
    parse = OptionParser(usage=usage, description=description)
    parse.add_option('-f', '--force', action="store_true", default=False,
        help='force the rasterization of the cities vector layer')
    parse.add_option('-c', '--cat', metavar='ID',
        help='run script on a single city cat ID number')
    parse.add_option('-t', '--maxtime', metavar='MINUTES', default='180',
        help='sets the max travel time per city')
    parse.add_option('-p', '--pop', metavar='FIELDNAME', default='POP2010',
        help='name of the population field within parse')
    parse.add_option('-P', '--preserve', default=False, action="store_true",
        help='preserves the individual city travel time maps (city##_tt)')
    parse.add_option('-r', '--rebuild', default=False, action="store_true",
        help='rebuild city travel time maps even if one exists')
    parse.add_option('-m', '--mode', default="grav",
        help='operate in either max or gravity mode (default=grav)')
    parse.add_option('-n', '--name', default="cities",
        help='the name of the output attractor (default=cities)')

    opts, args = parse.parse_args()
    if len(args) != 1:
        parse.error("'cities' layer name rquired")
    else:
        cities = args[0]

    if opts.mode == 'grav':
        dest = opts.name + '_att'
        method = '$dest=$dest+if(isnull($tt), 0.0, $pop/($tt+30.0)^2)'
        grass.mapcalc("$dest=0.0", dest=dest)
    elif opts.mode == 'max':
        dest = opts.name +'_max_att'
        method = '$dest=max($dest,if(isnull($tt), 0.0, $pop/($tt+0.1)^2))'
        grass.mapcalc("$dest=0.0", dest=dest)
    elif opts.mode == 'cost':
        dest = opts.name + '_cost'
        # the cost multiplies 100 to enlarge the difference so that
        # the cost can be viewable by the .tif map generated by grass
        method = '$dest=min($dest,if(isnull($tt), 9999.0, $tt*100))'
        grass.mapcalc("$dest=9999.0", dest=dest)
    else:
        parse.error("option mode must be max or gravity or cost")

    return cities, dest, method, opts.pop, opts.maxtime


def main():
    grass_config('grass', 'model')

    os.environ['GRASS_MESSAGE_FORMAT'] = 'silent'
    grass.run_command('g.gisenv', set='OVERWRITE=1')
    mapset = grass.gisenv()['MAPSET']
    
    cities, dest, method, colname, maxtime = parse_args()

    # ywkim added to figure out the number of class
    # create the list for the unique class category
    classSet = Set()
    numClass = grass.parse_command('v.db.select', flags='c', map=cities, column='cat,CLASS', fs='=')
    for cat,CLASS in numClass.items():
        classSet.add(int(CLASS))
    classList = list(classSet)
    print "classList: ", classList
    
    # calculate average population for each class
    classAveList = []
    for i in xrange(len(classList)):
        total = counter = 0
        classAve = grass.parse_command('v.db.select', flags='c', map=cities, 
            column='cat,'+colname, where='CLASS = '+str(classList[i]), fs='=')    
        for cat,pop in classAve.items():
            total += int(pop)
            counter += 1
        classAveList.append(total/counter)
    print "classAveList: ", classAveList
    
    for classVal, aveVal in zip(classList, classAveList):
        print "Class =  ", classVal, ", Average = " , aveVal
        classtravelcost = make_city_tt(cities, classVal, maxcost=maxtime)
        grass.mapcalc(method, dest=dest, pop=aveVal, tt=classtravelcost)

    # normalize(dest) ==> use .SFA
    grass.run_command('r.null', map=dest, null=0.0) 
    # As all multicost model maps' smallest values are 0,
    # it makes sense to set all null values to be 0.
    
    print dest, " created."

if __name__ == '__main__':
     main()

