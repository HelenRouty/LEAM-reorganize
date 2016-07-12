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

usage = "usage: %prog [options] <cities>"

description = """ Iterates through each city in the <cities> 
vector layer computing a city attractor map.  Each city attractor 
map is aggregated into the final <attmap> to create a cities gravity 
map using POP/(cityatt+1)^2.
"""

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

def normalize(layer, result=""):
    "normalize a composity gravity map"

    if (result==""):
        result=layer+"_norm_att"
    layer = layer+"_att"

    for l in os.popen('r.univar %s' % layer):
        if l.startswith('maximum:'):
            s, max = l.strip().split()
            os.system('r.mapcalc %s=%s/%s' % (result,layer,max))
            break

    # outfilename = 'Data/'+layer+'.tif'
    # if grass.run_command('r.out.gdal', input=layer, 
    #     output=outfilename, type='Float64'):
    #     raise RuntimeError('unable to export raster map ' + layer)

def make_city_tt(cities, cat, overland='overlandTravelTime30', 
                 interstates='intTravelTime30', xover='cross', maxcost='180'):
    """Extracts a specific city, buffers it, and then uses r.multicost
       to determine travel time out to maxcost (minutes), and computes
       attractor maps based on pop/tt^2.
       tt -- is the travel time map
    """

    """
    ywkim added, it originally extracts from the raster
    but it is not accurate if there are many points overlapped
    so change this to work using vector first then convert to raster
    """
    
    grass.run_command('v.extract', input=cities, output='ctmpv',
        where="class = %s" % (cat), overwrite=True, quiet=True)
    grass.run_command('g.region', res=30)
    #grass.mapcalc('ctmp=if($cities==$cat,1,null())', cities=cities,
    #    cat=cat)
    grass.run_command('v.to.rast', input='ctmpv', output='ctmp', 
        use='val', value=1, overwrite=True)
    #grass.run_command('g.remove', v='ctmpv')
    grass.run_command('r.buffer', input='ctmp', output='ctmp', dist='180')
    grass.mapcalc('ctmp=if(ctmp)')
    grass.run_command('r.multicost', input=overland, m2=interstates, 
        xover=xover, start_rast='ctmp', output='tt', max_cost=maxcost)

def main():
    grass_config('grass', 'model')
    os.environ['GRASS_MESSAGE_FORMAT'] = 'silent'
    grass.run_command('g.gisenv', set='OVERWRITE=1')
    mapset = grass.gisenv()['MAPSET']

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
    parse.add_option('-m', '--mode', default="max",
        help='operate in either max or gravity mode (default=max)')
    parse.add_option('-n', '--name', default="cities",
        help='the name of the output attractor (default=cities)')

    opts, args = parse.parse_args()
    # if len(args) != 1:
    #     parse.error("'cities' layer name rquired")
    # else:
    #     cities = args[0]

    # if opts.mode == 'grav':
    #     dest = opts.name + '_att'
    #     method = '$dest=$dest+if(isnull($tt), 0.0, $pop/($tt+40.0)^2)'
    #     grass.mapcalc("$dest=0.0", dest=dest)
    # elif opts.mode == 'max':
    #     dest = opts.name +'_max_att'
    #     method = '$dest=max($dest,if(isnull($tt), 0.0, $pop/($tt+0.1)^2))'
    #     grass.mapcalc("$dest=0.0", dest=dest)
    # elif opts.mode == 'cost':
    #     dest = opts.name + '_cost'
    #     # the cost multiplies 100 to enlarge the difference so that
    #     # the cost can be viewable by the .tif map generated by grass
    #     method = '$dest=min($dest,if(isnull($tt), 9999.0, $tt*100))'
    #     grass.mapcalc("$dest=9999.0", dest=dest)
    # else:
    #     parse.error("option mode must be max or gravity or cost")

    # # if the cat ID of the city has been given just create the city map
    # # NOTE: short-circuits the rest of the script!
    # if opts.cat:
    #     tt = make_city_tt(cities, opts.cat, maxcost=opts.maxtime)
    #     grass.run_command('g.rename', rast='%s,city%s_tt' % (tt,opts.cat))
    #     grass.message('city%s_tt: city travel time created.' % opts.cat)
    #     sys.exit(0)

    # # get all the existing travel time maps
    # ttmaps = grass.mlist_grouped('rast', pattern='city*_tt').get(mapset,[])
    
    # # ywkim added to figure out the number of class
    # # create the list for the unique class category
    # numClass = grass.parse_command('v.db.select', flags='c', map=cities, column='cat,CLASS', fs='=')
    # classList = []
    # classUniList = []
    # classAveList = []

    # for cat,CLASS in numClass.items():
    #     classList.append(int(CLASS))

    # classList.sort()
    
    # classStartValue = 0

    # for i in range(len(classList)):
    #     if classList[i] != classStartValue:
    #         classUniList.append(classList[i])
    #         classStartValue = classList[i]

    # # create the average number for the class
    # for i in range(len(classUniList)):
    #     totalNum = 0
    #     indexCounter = 0
    #     aveVal = 0
    #     classAve = grass.parse_command('v.db.select', flags='c', 
    #         map=cities, column='cat,'+opts.pop, where='CLASS = '+str(classUniList[i]), fs='=')    

    #     for cat,pop in classAve.items():
    #         totalNum = totalNum + int(pop)
    #         indexCounter = indexCounter + 1

    #     aveVal = totalNum / indexCounter
    #     classAveList.append(aveVal)

    # """
    # ywkim disabled this routine to make it class based routine
    # # for each city calculate the accumulated cost surface and
    # # convert gavity map by dividing population by cost squared and
    # # create a composite map gravity may be summing all maps together
    # catpop = grass.parse_command('v.db.select', flags='c', 
    #     map=cities, column='cat,'+opts.pop, fs='=')

    # for cat,pop in catpop.items():
    #     print cat, pop
    #     citytt = 'city%s_tt' % cat
    #     if opts.rebuild or citytt not in ttmaps:
    #         make_city_tt(cities, cat, maxcost=opts.maxtime)
    #         if opts.preserve:
    #             grass.run_command('g.rename', rast='tt,%s' % citytt)
    #         else:
    #             citytt = 'tt'
    #     grass.mapcalc(method, dest=dest, pop=pop, tt=citytt)

    # normalize(dest)
    # print dest, "created."
    # """

    # for i in range(len(classUniList)):
    #     classVal = classUniList[i]
    #     aveVal = classAveList[i]
    #     print "Class =  ", classVal, ", Average = " , aveVal
    #     citytt = 'city%s_tt' % classUniList[i]
    #     if opts.rebuild or citytt not in ttmaps:
    #         make_city_tt(cities, classVal, maxcost=opts.maxtime)
    #         if opts.preserve:
    #             grass.run_command('g.rename', rast='tt,%s' % citytt)
    #         else:
    #             citytt = 'tt'
    #     grass.mapcalc(method, dest=dest, pop=aveVal, tt=citytt)

    if opts.mode != 'cost':
        normalize(opts.name)
    # print dest, " created."

if __name__ == '__main__':
     main()

