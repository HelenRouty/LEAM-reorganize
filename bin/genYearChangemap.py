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
import subprocess
from subprocess import check_call
import grasssetup
from parameters import DEMANDGRAPH
from weblog import RunLog


###### Generate Yearly Demand Graph ######
def genYearlyDemandGraph(demandstr, projid):
    runlog.p("***parse the demand table to year and population and interpolate......")
    yr1, yr2, pop1, pop2 = getDemandYearPop(demandstr, 'Population')
    yearincrpoplist = interpolate(yr1, yr2, pop1, pop2)

    yr1, yr2, emp1, emp2 = getDemandYearPop(demandstr, 'Employment')
    yearincremplist = interpolate(yr1, yr2, emp1, emp2)

    # output increment demand per year relative to the start year.
    writeDemand(yearincrpoplist, yearincremplist, projid)

    return yr1, yr2


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


def writeDemand(yearincrpoplist, yearincremplist, title, 
                filename=DEMANDGRAPH):
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

###### Write GLUC Config File ######
def writeConfig(confname='baseline.conf',
                start='2010', end='2040',
                prefix='', probmaps=False,
                tmpl='gluc/Config/baseline.tmpl',
                path='gluc/Config'):
    """ write a GLUC config file from a template.

    PREFIX,START_DATE, and END_DATE are replaced in the template. PREFIX
    is applied to probability maps name but the START_DATE is not.  The
    GLUC model automatically appends the year during model execution.

    @confname - name of config file to be written (.conf appended if needed)
    @prefix - prefix applied to probmap names (growth, decline)
    @start - fills the START_DATE parameter in the template
    @end - fills the END_DATE parameter in the template
    @probmaps - toggle initial and final probmaps writing 
    @tmpl - name of the temlate config file
    @path - destination for 
    @Return - nothing
    # function copied from original startup.py
    """
    # runlog.debug('writeConfig: confname=%s, prefix=%s, start=%s, end=%s' % \
    #              (confname, prefix, start, end))

    # cleanup confname and add path
    grasssetup.grassConfig()
    grass = grasssetup.grass
    if not confname.endswith('.conf'):
        confname += '.conf'
    config = os.path.join(path, os.path.basename(confname))

    # read the template file into string
    with open(tmpl, 'r') as f:
        template = f.read()

    d = dict(PREFIX=prefix, START_DATE=start, END_DATE=end)
    with open(config, 'w') as f:
        f.write(template.format(**d))
        if probmaps:
            f.write('* INITIAL_PROB_RES_MAP    M(M, 4, initial_probmap_res)\n')
            f.write('* INITIAL_PROB_COM_MAP    M(M, 4, initial_probmap_com)\n')
            f.write('* FINAL_PROB_RES_MAP      M(M, 4, final_probmap_res)\n')
            f.write('* FINAL_PROB_COM_MAP      M(M, 4, final_probmap_com)\n')
        if grass.find_file('pop_density', element='cell'):
            f.write('* DENSITY_MAP_RES         d(M, pop_density.bil)\n')

        if grass.find_file('emp_density', element='cell'):
            f.write('* DENSITY_MAP_COM         d(M, emp_density.bil)\n')

###### Generate GLUC Bil File Inputs #######
def genBilGLUCInputs():
    grasssetup.grassConfig()
    grass = grasssetup.grass

    grass.run_command('r.out.gdal', input='boundary', 
        output='gluc/Data/boundary.bil', format='EHdr', type='Byte')
    grass.run_command('r.out.gdal', input='landcover',
        output='gluc/Data/landcover.bil', format='EHdr', type='Byte')
    grass.run_command('r.out.gdal', input='nogrowth', 
        output='gluc/Data/nogrowth.bil', format='EHdr', type='Byte')
    grass.run_command('r.out.gdal', input='probmap_res',
        output='gluc/Data/growth_probmap_res.bil', format='EHdr', type='Float32')
    grass.run_command('r.out.gdal', input='probmap_com',
        output='gluc/Data/growth_probmap_com.bil', format='EHdr', type='Float32')
    
    if grass.find_file('pop_density', element='cell'):
        grass.run_command('r.out.gdal', input='pop_density', 
            output='gluc/Data/pop_density.bil', format='EHdr',type='Float32') # needs to be Float32
        runlog.p('***use uploaded pop_density in GLUC')
    else:
        runlog.p('***use GLUC default pop_density')

    if grass.find_file('emp_density', element='cell'):
        grass.run_command('r.out.gdal', input='emp_density', 
            output='gluc/Data/emp_density.bil', format='EHdr', type='Float32') # needs to be Float32
        runlog.p('***use uploaded emp_density in GLUC')
    else:
        runlog.p('***use GLUC default emp_density')

###### Execute GLUC ######
def executeGLUCModel(demandstr, projid, log, mode='growth'):
    """***GLUC model requires inputs***
       1. demand.graph                      --- genYearlyDemandGraph
       2. ${projid}.conf configuration file --- writeConf
       3. boundary, landcover, nogrowth, pop_density, emp_density, probmap_com, probmap_res
          .bil && .hdr files                --- genBilGLUCInputs
       4. empty change and summary .bil && .hdr files 
                                            --- gluc.make start
       ***GLUC model run***
       gluc.make growth

       ***GLUC model outputs***
       change.bil and summary.bil in gluc/DriverOutput/Maps
    """
    global runlog
    runlog = log
    # generate GLUC model inputs
    runlog.p("--generate yearly demand graph according to demand year and population........")
    startyear, endyear = genYearlyDemandGraph(demandstr, projid)
    runlog.p("--generate GLUC model configuration file........")
    writeConfig(confname=projid, prefix=mode+'_', start=startyear, end=endyear)
    runlog.p("--generate GLUC input .bil maps........")
    genBilGLUCInputs()
    runlog.p("--generate empty GLUC result change and summary maps")
    cmd = 'make -f bin/gluc.make start'
    check_call(cmd.split())
    
    runlog.h("\nRun GLUC model.....................")
    try:
        with open('./Log/%s_gluclog.log' % projid, 'w') as log:
            cmd='make -f bin/gluc.make %s PROJID=%s START=%s'% (mode, projid, startyear)
            check_call(cmd.split(), stdout=log, stderr=log)
    except subprocess.CalledProcessError:
        runlog.warn('GLUC Model Failure')
        sys.exit(5)


def main():
    # Sample variable values
    # scenariotitle = 'test2_projection'
    # resultsdir = 'http://portal.leam.illinois.edu/chicago/luc/scenarios/test4_scenario'
    # demandgraphurl="http://portal.leam.illinois.edu/chicago/luc/projections/test2_projection/getGraph"

    resultsdir = sys.argv[1]
    scenariotitle = os.path.basename(resultsdir)

    global site
    global runlog
    site = LEAMsite(resultsdir, user=sys.argv[2], passwd=sys.argv[3])
    runlog = RunLog(resultsdir, site, initmsg='Scenario ' + scenariotitle)

    demandgraphurl = sys.argv[4]
    demandstr = site.getURL(demandgraphurl).getvalue()

    executeGLUCModel(demandstr, scenariotitle, runlog)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Require Arg1: resultsdir, Arg2: username, ",\
              "Arg3: password to connect to plone site, Arg4: demandgraphurl for expected population change."
        exit(1)
    main()
