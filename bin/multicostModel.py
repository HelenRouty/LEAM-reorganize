#!/usr/bin/env python
import os
import sys
import time
sys.path += ['..']
from glob import iglob
from leamsite import LEAMsite
from parameters import *
from genSimMap import genSimMap, genclassColorCondlist
from weblog import RunLog

"""Organized from original LEAM attrmap.make and probmap.make.
   TODO: merge basic GRASS functions to the grasssetup.py.
   mygrass.py in privious LEAM code is a better reference.
"""

######################## Basic GRASS and site setup Functions #################################
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
    grass.run_command('g.region', res=30)  


def importVector(fullpathfilename, layername):
    if grass.run_command('v.in.ogr', flags='o', dsn=fullpathfilename,
            snap='0.01', output=layername, overwrite=True, quiet=True):
        raise RuntimeError('unable to import vectormap ' + layername) 


def exportRaster(layername, valuetype='Float64'): #'UInt16'
    outfilename = 'Data/'+layername+'.tif'
    if grass.run_command('r.out.gdal', input=layername, 
      output=outfilename, type=valuetype, quiet=True):
        raise RuntimeError('unable to export raster map ' + layername )


def export_asciimap(layername, nullval=-1, integer=False):
    """Export a raster layer into asciimap. The output folder is 'Data/'.
       @param: layername (str)     the raster layer name.
               nullval   (int)     the output for null value.
               integer   (boolean) if the ascii is integer or Float64
    """
    outfilename = 'Data/'+layername+'.txt'
    if integer==True:
        if grass.run_command('r.out.ascii', input=layername, output=outfilename, 
            null=nullval, quiet=True, flags='i'):
            raise RuntimeError('unable to export ascii map ' + layername)
    else:
        if grass.run_command('r.out.ascii', input=layername, output=outfilename, 
            null=nullval, quiet=True):
            raise RuntimeError('unable to export ascii map ' + layername)


def publishSimMap(maptitle, site, url, description='',
                  numcolors=NUMCOLORS, regioncode=CHICAGOREGIONCODE):
    """Publish the raster map .tif to the website.
       @ inputs: maptitle (str) the output map name
                 description (str) the description to be shown for each map on the website
                 site (str) the website to be published to.
                 url  (str) a specific senario url
                 numcolors (int) the number of colors to be assigned to the map
                       the actual number of colors may be less than expected
                 regioncode (int) the epsg region code. Chicago is 26196.
    """
    simmap  = 'Data/%s.tif' % maptitle
    mapfile = 'Outputs/%s.map' % maptitle

    classColorCondlist = genclassColorCondlist(maptitle, numcolors)
    genSimMap(regioncode, classColorCondlist, maptitle)

    popattrurl = site.putSimMap("%s.tif" % maptitle, "%s.map" % maptitle, url,
        simmap_file=open(simmap, 'rb'), 
        mapfile_file=open(mapfile, 'rb'))
    site.updateSimMap(popattrurl, title=maptitle, description=description)


def exportAllforms(maplayer, valuetype='Float64', description=''):
    """ Float64 has the most accurate values. However, Float64
        is slow in processing the map to show in browser. 'UInt16' 
        is the best.
    """
    exportRaster(maplayer, valuetype)
    if valuetype == 'UInt16':
        export_asciimap(maplayer, integer=True)
    else:
        export_asciimap(maplayer)
    publishSimMap(maplayer, site, resultsdir, description)

################## Fucntions for centers and travel time maps #################
######  Required files in GRASS: otherroadsBase, landcover ########
def genotherroads():
    """@input map: otherroads (vect)
       @output map: otherroads (rast) 
                    with value = class in vector map and null = 0
    """
    grass.run_command('v.to.rast', input='otherroads', 
        output='otherroads', column='class')
    grass.run_command('r.null', map='otherroads', null=0)

def geninterstatesBaseAndinterstates():
    """Generate interstatesBase and interstates map, the
       interstates roads extracted from roadnetwork for 
       genoverlandTravelTime30 and genintTravelTime30
       @input map: otherroads
       @output maps: interstatesBase, interstates
    """
    # otherroads -> interstatesBase
    grass.run_command('v.extract', input='otherroads',
        output='interstatesBase', where="class = 1")
    grass.run_command('v.to.rast', input='interstatesBase', 
        output='interstatesBase', column='class')
    grass.run_command('r.null', map='interstatesBase', null=0)
    # interstatesBase -> interstates
    grass.mapcalc ("interstates=if(interstatesBase==0,0,1)")


def gencross():
    """Generate map cross - the intersection of interstates and ramp
       - for r.multicost function
       @input maps: interstates, otherroads
       @output map: cross
    """
    # interstates, otherroads -> cross
    grass.run_command('r.buffer',flags='z', input='interstates',
        output='intbuf', dist=60) # z to ignore zero value data cells
    grass.mapcalc('cross=if(intbuf && otherroads==6, 1, 0)')
    grass.run_command('g.remove', rast='intbuf')


def genoverlandTravelTime30():
    """Generate traveltime map: overlandTravelTime30
       @input maps: landcover, otherroads interstates
       @intermediate maps: landTravelSpeed30, othTravelSpeed30,
                           overlandTravelSpeed30
       @output map: overlandTravelTime30 
    """
    # landcover -> landTravelSpeed30
    grass.run_command('r.recode', input="landcover", 
        output="landTravelSpeed30", rules=GRAPHS+"/lu_speeds.recode")
    # otherroads ->otherroadsSpeedBase = othTravelSpeed30
    grass.run_command('v.to.rast', input="otherroads", 
        output="othTravelSpeed30", col="speed")
    grass.run_command('r.null', map='othTravelSpeed30', null=0)

    # othTravelSpeed30, landTravelSpeed30, interstates -> overlandTravelSpeed30
    grass.mapcalc("overlandTravelSpeed30=if(othTravelSpeed30, \
        othTravelSpeed30,if(interstates,0,landTravelSpeed30))")
    # overlandTravelSpeed30 -> overlandTravelTime30
    grass.mapcalc("overlandTravelTime30 =if($speed>0,1.8/$speed, null())", 
        speed="overlandTravelSpeed30")


def genintTravelTime30():
    """Gnereate traveltime map: intTravelTime30, the travel time 
       cost per cell for roads only using roadnetwork transport/road type
       and transport/road speed.
       @input maps: interstatesBase
       @intermediate maps: intTravelSpeed30
       @output mpa: intTravelTime30
    """
    # interstatesBase -> interstatesSpeedBase = intTravelSpeed30
    grass.run_command('v.to.rast', input="interstatesBase",
        output="intTravelSpeed30", col="speed")
    # intTravelSpeed30 -> intTravelTime30
    grass.mapcalc("intTravelTime30 =if($speed>0,1.8/$speed, null())", 
        speed="intTravelSpeed30")

    exportRaster('intTravelTime30')

################# Multicost to Travel Time On Roads Model ###################
##### this function is a sample to be used in cities.py #####
def multicost4travelcost(centersMap, outputname, maxcostmin):
    grass.run_command('r.multicost', input="overlandTravelTime30", 
        m2="intTravelTime30", xover="cross", start_rast=centersMap, 
        output=outputname, max_cost=maxcostmin)
    exportRaster(outputname)

################## Caculate Roads Attraction #################################
######  Required files in GRASS: otherroads #########
def roadsTravelCost(roadsClassName_list=[('staterd', 2), ('county', 3), ('road', 4), ('ramp', 6)]):
    """This takes about 3min.
    """
    for layername, classnum in roadsClassName_list:
        start = time.time()
        outname = str(layername)+"_cost"
        runlog.p("***caculating %s......" % outname)
        grass.mapcalc('centers=if(otherroads==' + str(classnum) + ',1,null())')
        grass.run_command('r.multicost', input="overlandTravelTime30",
            m2="intTravelTime30", xover="cross", start_rast="centers", 
            output=outname)
        exportAllforms(outname, 'UInt16')
        print outname," takes ", time.time()-start,"s."


def intersectionTravelCost(layername="intersect_cost"):
    """Finds state #2 and county #3 road  intersections.  Create a map of
       just state and county roads. Expand these locations by one cell and
       then thin them down to one cell (to take care of any small map errors).
       Then find cells that are surrounded by more than two cells containing
       roads.
    """
    grass.run_command('g.region', res=30)
    grass.mapcalc('int1=if((otherroads==2) || (otherroads==3), 1, 0)')
    grass.run_command('r.thin', input="int1", output="int2")
    grass.run_command('r.null', map="int2", null=0)
    grass.mapcalc('intersection=if(int2==1,  \
      if(2<(int2[-1,-1]+int2[-1,0]+int2[-1,1]+ \
            int2[ 0,-1]           +int2[ 0,1]+ \
            int2[ 1,-1]+int2[ 1,0]+int2[ 1,1]) ,1,0))')
    grass.run_command('r.null', map='intersection', setnull=0)
    
    grass.run_command('r.multicost', input="overlandTravelTime30",
            m2="intTravelTime30", xover="cross", start_rast="intersection", 
            output=layername)
    grass.run_command('g.remove', rast=["int1","int2", "intersection"])


def transportAttraction(layername="transport_att"):
    grass.mapcalc(layername+"="+str(W_STATERD)+"/(staterd_cost+0.1) + "
                               +str(W_COUNTY)+"/(county_cost+0.1) + "
                               +str(W_ROAD)+"/(road_cost+0.1) + "
                               +str(W_RAMP)+"/(ramp_cost+0.1) + "
                               +str(W_INTERSECT)+"/(intersect_cost+0.1)")
    grass.run_command('r.null', map=layername, null=0.0)

##################### Water and Forest Attraction ########################
######  Required files in GRASS: landcover #########
def watercondstr():
    return "(landcover==11)"
def forestcondstr():
    """41=deciduous forest, 42=evergreen forest, 43=mixed forest, 91=woody wetland"""
    return "(landcover==41 || landcover==42 || landcover==43 || landcover==91)"
def bufferAttraction(layername, layercond_str):
    grass.mapcalc('int1=if' + layercond_str)
    grass.run_command('r.buffer', flags='z', input='int1', output='int2',
       distances=[30,60,90,120,150,180,210,240,270,300,330,360])
    grass.mapcalc(layername+'=if(isnull(int2),390,(int2-1)*30)')
    grass.run_command('g.remove', rast=["int1","int2"])

##################### Slope Attraction ########################
######  Required files in GRASS: demBase #########
def genslopeCost(layername="slope_cost"):
    """Caculate slope attraction
       @input: demBase
       @output: slope_att
    """
    grass.run_command('r.slope.aspect', elevation="demBase", slope="int1")
    grass.mapcalc(layername+'=round(int1)')
    grass.run_command('g.remove', rast="int1")

##################### Transform Attrmaps to scores ######################
####### Required files: sfa files in ./SFA folder. ##########
def cost2score(costname, scorename):
    """Transform attractiveness map to a score map using SFA files.
       @input: attractiveness map without _cost
       @output: result score map name
    """
    grass.run_command('r.recode', input=costname+'_cost', output=scorename+"_score", 
                                  rules="SFA/"+scorename+".sfa")
    # Setting to null so that there won't be weird values appear
    grass.run_command('r.null', map=scorename+"_score", null=0.0)
    return scorename+"_score"


def att2score_centers(attname, scorename):
    """Transform attractiveness map to a score map using SFA files.
       @input: attractiveness map without _att
       @output: result score map name
    """
    grass.run_command('r.recode', input=attname+"_att", output=scorename+"_score", 
                                  rules="SFA/"+scorename+".sfa")
    weight = WEIGHTS[scorename]
    grass.mapcalc('%s_score=pow(%s_score,%f)' %(scorename, scorename, weight))
    export_asciimap(scorename+"_score")
    return scorename+"_score"


def genProbmap(centerscorelist, costscorelist, problayername, multiplier=100000):
    """ From attrmaps to generate probmap.
        @input: centerscorelist is a list of (attname, scorename) pairs. 
                E.g. centerscorelist can be:
                [('pop', 'pop_com'), ('emp', 'emp_com'),
                 ('transport', 'transport_com')] for 'probmap_com' map.
                costlist can be [('forest', 'forest'), ('water', 'water'), ('slope', 'slope')]
                multiplier is hard coded to multiply a integer to the final probmap.
                TODO: multiplier should be an automate process.
        @output: probmap_com or probmap_res (commercial/residential)
                 probmap_com_percentage or probmap_res_percentage
                 _percentage maps are probmap * 100 to have integer values to 
                 speed up showing on browser.
    """
    grass.mapcalc(problayername+'=1.0')
    for cost, score in costscorelist:
        score = cost2score(cost, score)
        grass.mapcalc(problayername +'='+ problayername + '*' + score)
    for att, score in centerscorelist:
        score = att2score_centers(att, score)
        grass.mapcalc(problayername +'='+ problayername + '*' + score) 
    grass.mapcalc("%s_percentage = %s*%i" %(problayername, problayername, multiplier))    
    grass.run_command('g.remove', rast=score)

##################### Main Functions to be called ######################
def gencentersAttmaps(empcenters, popcenters):
    # pop/emp centers attractive maps require landTravelTime30 and intTravelTime30
    runlog.p("--generate otherroads, the raster form of roadnetwork......")
    genotherroads()
    exportAllforms('otherroads', 'UInt16') # otherroads have road class 1-6
    
    runlog.p("--generate interstatesBase, the interstates roads (class 1) extracted from roadnetwork......")
    geninterstatesBaseAndinterstates()
    exportAllforms('interstates', 'UInt16')
    
    runlog.p("--generate cross, the intersection of interstates and ramps......")
    gencross()
    exportAllforms('cross', 'UInt16')     # cross has values either 0 or 1
    
    runlog.p("--generate overlandTravelTime30, the travel time cost per cell, "
               "using landuse map and landuse type speed table......")
    genoverlandTravelTime30()
    exportAllforms('overlandTravelTime30')# overlandTravelTime30 is (0, 1) 
    
    runlog.p("--generate intTravelTime30, the travel time cost per cell, "
               "using the 'CLASS' and 'SPEED' values in roadnetwork map......") 
    genintTravelTime30()                  # intTravelTime30 has one uniq value
    exportAllforms('intTravelTime30', 'UInt16')

    runlog.p("--generate population centers attractive map using cross, "
               "overlandTravelTime30, intTravelTime30, and population centers......")
    os.system("python bin/cities.py -p total_pop -n pop -m grav popcentersBase > Log/popatt.log")
    exportAllforms("pop_att", 'UInt16')

    runlog.p("--generate population centers travelcost map......")
    os.system("python bin/cities.py -p total_pop -n pop -m cost popcentersBase > Log/popcost.log")
    exportAllforms("pop_cost", 'UInt16')

    runlog.p("--generate employment centers attractive map using cross, "
               "overlandTravelTime30, intTravelTime30, and employment centers......")
    os.system("python bin/cities.py -p total_emp -n emp -m grav empcentersBase > Log/empatt.log")
    exportAllforms("emp_att", 'UInt16')

    runlog.p("--generate employment centers travelcost map......")
    os.system("python bin/cities.py -p total_emp -n emp -m cost empcentersBase > Log/empcost.log")
    exportAllforms("emp_cost", 'UInt16')

def genOtherAttmaps():
    # print "--generate staterd, county, road, and ramp attractiveness..."
    runlog.p("--generate travel cost map for each road class type except for interstates......")
    roadsClassName_list = [('staterd', 2), ('county', 3), ('road', 4), ('ramp', 6)]    
    roadsTravelCost(roadsClassName_list)
    
    runlog.p("--generate intersection travel cost map......")
    intersectionTravelCost()
    exportAllforms("intersect_cost", 'UInt16')

    runlog.p("--generate transport attraction map using statered_cost, "
               "county_cost, road_cost, ramp_cost, and intersect_cost......")
    transportAttraction()
    exportAllforms("transport_att", 'UInt16')
    
    runlog.p("--generate water travelcost map......")
    bufferAttraction("water_cost", watercondstr())
    exportAllforms("water_cost", 'UInt16')

    runlog.p("--generate forest travelcost map......")
    bufferAttraction("forest_cost", forestcondstr())
    exportAllforms("forest_cost", 'UInt16')

    runlog.p("--generate slope travelcost map......")
    genslopeCost()
    exportAllforms("slope_cost", 'UInt16')


def genProbmaps():
    runlog.p("--generate probmap_com, the probabiltiy map for commertial developement, "
               "and output probmap_com_percentage, where all values are 0.01 of probmap_com......")
    genProbmap(COMSCORELIST, COSTSCORELIST, 'probmap_com', 10000000)# probcom has -07 values
    exportAllforms('probmap_com_percentage') 

    runlog.p("--generate probmap_res...the probabiltiy map for residential developement, "
             "and output probmap_res_percentage, where all values are 0.01 of probmap_res......")
    genProbmap(RESSCORELIST, COSTSCORELIST, 'probmap_res', 100000)
    exportAllforms('probmap_res_percentage')

def runMulticostModel(resultsurl, website, log):
    global resultsdir
    global site
    global runlog
    resultsdir = resultsurl
    site = website
    runlog = log
    grassConfig('grass', 'model')

    gencentersAttmaps(EMPCENTERS, POPCENTERS)
    genOtherAttmaps()
    genProbmaps()



def main():
    sys.stdout = open('./Log/multicostModel.stdout.log', 'w')
    sys.stderr = open('./Log/multicostModel.stderr.log', 'w')

    # exportRaster('emp_centers4_47_98')
    # importVector('Data/FID4_47_98', EMPCENTERS) 
    # print "list available raster maps in database..."
    # grass.run_command('g.mlist', type='rast')   
    resultsdir = sys.argv[1]
    user = sys.argv[2]
    passwd = sys.argv[3]
    site = LEAMsite(resultsdir, user, passwd)
    global runlog
    runlog = RunLog(resultsdir, site, initmsg='Scenario ' + scenariotitle)
    runMulticostModel(user, passwd, runlog)
    
     
if __name__ == "__main__":
    main()