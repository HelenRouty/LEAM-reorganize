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
from Utils import createdirectorynotexist
from subprocess import check_call

scenatriotitle = 'test2_projection'
resultsdir = 'http://portal.leam.illinois.edu/chicago/luc/scenarios/test4_scenario'
DEMANDGRAPH ='gluc/Data/demand.graphs'

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
        results.append((x1+i, int(round(i*delta, 0))))
    results.append((x2,y2-y1))
    return results

def writeDemand(yearincrpoplist, yearincremplist, 
    title=scenatriotitle, filename=DEMANDGRAPH):
    # concatenate the year, population to string to demand.graph file.
    outstrlist = ['# %s\n\nPopulation\n'%title]
    for yr, pop in yearincrpoplist:
        outstrlist.append('%s, %s\n' % (str(yr), str(pop)))
    outstrlist.append('\n\nEmployment\n')
    for yr, emp in yearincremplist:
        outstrlist.append('%s, %s\n' % (str(yr), str(emp)))

    createdirectorynotexist(filename)
    with open(filename, 'w') as f:
        f.write(''.join(outstrlist))

def genYearlyDemandGraph():
    # fetch demand table from website
    demandurl = "http://portal.leam.illinois.edu/chicago/luc/projections/test2_projection/getGraph"
    demandstr = site.getURL(demandurl).getvalue()
    
    # parse the demand table to year and population and interpolate
    yr1, yr2, pop1, pop2 = getDemandYearPop(demandstr, 'Population')
    yearincrpoplist = interpolate(yr1, yr2, pop1, pop2)

    yr1, yr2, emp1, emp2 = getDemandYearPop(demandstr, 'Employment')
    yearincremplist = interpolate(yr1, yr2, emp1, emp2)

    # output increment demand per year relative to the start year.
    writeDemand(yearincrpoplist, yearincremplist)

def genBilGLUCInputs():
    grass.run_command('r.out.gdal', input='boundary', 
        output='gluc/Data/boundary.bil', format='EHdr', type='Byte')
    grass.run_command('r.out.gdal', input='landcoverBase',
        output='gluc/Data/landcover.bil', format='EHdr', type='Byte')
    grass.run_command('r.out.gdal', input='nogrowth', 
        output='gluc/Data/nogrowth.bil', format='EHdr', type='Byte')
    grass.run_command('r.out.gdal', input='pop_density', 
        output='gluc/Data/pop_density.bil', format='EHdr',type='Float32')
    grass.run_command('r.out.gdal', input='emp_density', 
        output='gluc/Data/emp_density.bil', format='EHdr', type='Float32') 

def executeGLUCModel(mode='growth', projid=scenatriotitle):
    """***GLUC model requires inputs***
       1. ${projid}.conf configuration file --- writeConf
       2. demand.graph                      --- genYearlyDemandGraph
       3. boundary, landcover, nogrowth, pop_density, emp_density
          .bil && .hdr files                --- genBilGLUCInputs
       4. empty change and summary .bil && .hdr files 
                                            --- gluc.make start
       ***GLUC model run***
       gluc.make growth

       ***GLUC model outputs***
       change.bil and summary.bil in gluc/DriverOutput/Maps
    """
    # generate GLUC model inputs
    # TODO: write PROJID.conf
    genYearlyDemandGraph()
    exit(1)
    genBilGLUCInputs()

    cmd = 'make -f gluc.make start'
    check_call(cmd.split())

    # run GLUC model
    try:
        with open('./Log/%s_gluclog.log' % scenatriotitle, 'w') as log:
            cmd='make -f gluc.make %s PROJID=%s'% (mode, projid)
            check_call(cmd.split(), stdout=log, stderr=log)
    except subprocess.CalledProcessError:
        print 'GLUC Model Failure'
        sys.exit(5)

def main():
    global site
    site = LEAMsite(resultsdir, user=sys.argv[1], passwd=sys.argv[2])
    grassConfig()

    executeGLUCModel()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Require Arg1: username, Arg2: password to connect to plone site."
        exit(1)
    main()
