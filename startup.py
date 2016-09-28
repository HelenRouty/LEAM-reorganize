import os
import sys
import time
sys.path += ['./bin']
from optparse import OptionParser
import requests
import subprocess
from subprocess import call
from subprocess import check_call
from zipfile import ZipFile
from zipfile import BadZipfile
from glob import iglob
from osgeo import ogr

# files in ./bin
from luc_config import LUC
import grasssetup
from leamsite import LEAMsite
from weblog import RunLog
from projectiontable import ProjTable
from Utils import createdirectorynotexist
import genYearChangemap # parameters are imported in genYearChangemap
from multicostModel import * # publishSimMap
from parameters import NUMCOLORS, CHICAGOREGIONCODE

"""
TODO:
***zip model results, intermediate maps folder and map results folder
2. descriptions for uploaded maps (store in parameters.py)
***cache probmap function
***projTable upload (GLUC)
***Delete files in ./Data, ./Inputs, and some files in ./grass to save space if sccessful
7. merge basic grass functions to grasssetup and mygrass.py(original LEAM code)
8. Add data analysis to the program and output results to plone.
9. sanity check
10. delete ./Inputs/projection_demand.txt from svn folder (make sure it's ok)
***allow no popdensity and empdensity to be uploaded and use a defualt caculation
    for uniform densities to be read by GLUC.
"""

######################## Basic Setups and Helper functions #################################
def parseFlags():
    """Three optional arguments required: projectid, user, and password
    """
    usage = "Usage: %prog [options] arg"
    parser = OptionParser(usage=usage, version='%prog')
    parser.add_option('-c', '--config', metavar='FILE', default=False,
        help='configuration FILE (default=stdin)')
    parser.add_option('-U', '--user', default=None,
        help='Portal user name (or PORTAL_USER environmental var)')
    parser.add_option('-X', '--password', default=None,
        help='Portal password (or PORTAL_PASSWORD environmental var)')

    (options, args) = parser.parse_args()

    # supervisor configuration will parse user and password to leampoll
    # and leampoll will set PORTAL_USER and PORTAL_PASSWORD before 
    # run this startup.py
    user = options.user or os.environ.get('PORTAL_USER', '')
    password = options.password or os.environ.get('PORTAL_PASSWORD', '')

    if not user or not password:
        sys.stderr.write('User and password information is required. '
                'Please set using -U <username> and -X <password> '
                'on command line or using environmental variables.\n')
        exit(1)

    if not options.config:
        sys.stderr.write('Config file url or filename is required. '
            'Please set using -c <configurl> on command line.\n')
        exit(1)

    return options.config, user, password


def get_config(configurl, user, password, configfile='config.xml'):
    """get the configuration from any one of multiple sources
       @inputs: configurl (str): URL or file name
                user (str): portal user 
                password (str): portal password
                configfile (str): name of the config file to be written
    """
    if os.path.exists(configfile):
        return configfile
    print configurl
    try: 
        r = requests.get(configurl, auth=(user, password))
        r.raise_for_status()
        config = r.text
    except:
        e = sys.exc_info()[0]
        print ("Error: Cannot access configuration file in url %s. %s"
                % (configurl, e))
        exit(1)

    with open(configfile, 'w') as f:
        f.write(config)

    return configfile


def get_grassfolder(url, user, password, fname='grass.zip'):
    """download an empty GRASS folder to the current repository
       If a local grass folder exist, new grass folder unzip abort.
       @inputs: uri (str): URL for download
                user (str): portal user
                password (str): portal password
                fname (str): tmp name for the GRASS location
    """
    r = requests.get(url, auth=(user, password), stream=True)
    r.raise_for_status()

    with open(fname, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*1024):
            f.write(chunk)

    if r.headers.get('content-type').startswith('application/zip'):
        with open(os.devnull, 'wb') as FNULL:
            check_call(['unzip', '-o', fname], 
                        stdout=FNULL, stderr=subprocess.STDOUT)
    os.remove('grass.zip')


def get_rasters(url, downloaddir='./Inputs'):
    """Download file and handle nonexist file.
       If not exist, an empty list returned. Hack...
       TODO: more elegent solution
    """
    try:
        fname = site.saveFile(url, dir=downloaddir)
        zipfname = '%s/%s' % (downloaddir, fname)
        print "***%s found, downloading as %s..." % (fname, zipfname)
        z = ZipFile(zipfname)
    except BadZipfile:
        print "***bad zip file"
        return [fname, ]
    # TODO fix error handling ???
    except:
        print "***empty zip file"
        return []

    rasters = []
    print "     zipped file namelist: ", z.namelist()
    for fname in z.namelist():
        if fname.endswith('/'):
            continue
        else:
            fname = os.path.basename(fname)
            rasters.append(fname)
            outfname = '%s/%s' % (downloaddir, fname)
            print "***get_raster: %s" % outfname
            with open(outfname, 'wb') as f:
                f.write(z.read(fname))
    os.remove(zipfname)
    print "***remove %s" % zipfname
    return rasters


def get_shapefile(url, downloaddir='./Inputs'):
    """Download zipped shape file from the url to downloaddir
       @output: name of the shapefile with downloaddir and unzipped folder
    """
    # Note: we currently read the entire uncompressed content of
    # a file into a string and then write it to file.  Python 2.6
    # provides a mechanssm for reading files piecemeal.
    try:
        if url.startswith('file://'):
            z = ZipFile(url.replace('file://',''))
        else:    
            z = ZipFile(site.getURL(url))
    except BadZipfile:
        raise RuntimeError('%s is not zip file' % url)

    # processes each file in the zipfile because embedded
    # directories are also part of the namelist we exclude
    # any filename ending with a trailing slash
    shapefile = None
    for zname in z.namelist():
        if zname.endswith('/'):
            continue
        else:
            fname = os.path.basename(zname)
            shapefolder = fname.split('.')[0]
            fname = '%s/%s/%s' %(downloaddir, shapefolder, fname)
            if fname.endswith('.shp'):
                shapefile = fname
            createdirectorynotexist(fname)
            with open(fname, 'wb') as f:
                content = z.read(zname)
                f.write(content)

    if not shapefile:
        raise RuntimeError('%s did not contain a shapefile' % url)
    return shapefile


def grass_safe(s):
    """Generate a string that is safe to use as a GRASS layer.

    Designed to handle filename with path and extensions but should
    work on any string. Currently performs the following steps:
    1) removes filename extension from basename and strip whitespace
    2a) removes any none alphabetic characters from the beginning
    2b) removes anything that does match a-z, A-Z, 0-9, _, -, or whitespace
    3) replaces remaining whitespaces and dashes with an _
    """
    s = os.path.splitext(os.path.basename(s))[0].strip()
    return re.sub('[\s-]+', '_', re.sub('^[^a-zA-Z]+|[^\w\s-]+','', s))


def import_rastermap(fname, layer=''):
    """Import a raster layer into GRASS

    Uses grass_safe to convert filename into a layer name if none is provided.
    @returns string - layer name
    """
    # runlog.debug('import_rastermap %s' % fname)
    if not layer:
        layer = grass_safe(fname)
    proj = grass.read_command('g.proj', flags='wf')
    fname = './Inputs/%s' % fname
    with open(os.devnull, 'wb') as FNULL:
        check_call(['gdalwarp', '-t_srs', proj, fname, 'proj.gtif'], 
                   stdout=FNULL, stderr=subprocess.STDOUT)
    if grass.find_file(layer)['name']:
        grass.run_command('g.remove', flags='f', rast=layer)
    if grass.run_command('r.in.gdal', _input='proj.gtif', output=layer,
            overwrite=True, quiet=True):
        raise RuntimeError('unable to import rastermap ' + fname)
    os.remove('proj.gtif')
    return layer


def clean_fields(sname, fields=('cat', 'cat_', 'CAT', 'CAT_', 'Cat')):
    """remove fields from vector layer
       NOTE: Somewhat convoluted because of OGR design, after the field is 
       deleted the field count becomes invalid.  So the for loop is restarted
       until no more matching fields are found.
    """
    shape = ogr.Open(sname, 1)
    if not shape:
        raise RuntimeError('unable to open projected shapefile')
    layer = shape.GetLayer(0)

    mods = True
    while mods:
        mods = False
        ldef = layer.GetLayerDefn()
        for i in range(ldef.GetFieldCount()):
            if ldef.GetFieldDefn(i).GetName().lower() in fields:
                print "print lower layer name: ", ldef.GetFieldDefn(i).GetName().lower()
                layer.DeleteField(i)
                mods = True
                break
    # Should call DestroyDataSource but doesn't seem to exist


def import_vectormap(fname, layer=''):
    """Import a vector layer into GRASS.
       Uses grass_safe to convert filename into a layer name if none is provided.
       NOTE: snap and min_area values are hardcoded and may not be appropriate
       for all projects
       @output: layer(str): layer name
       TODO: not sure why making this function so complicated. This is a legacy.
    """
    if not layer:
        layer = grass_safe(fname)

    # remove temporary previously projected shape files
    for f in iglob('proj.*'):
        os.remove(f)

    proj = grass.read_command('g.proj', flags='wf')

    check_call(['ogr2ogr', '-t_srs', proj, 'proj.shp', fname])
    clean_fields('proj.shp')

    if grass.run_command('v.in.ogr', flags='w', dsn='proj.shp',
           snap='0.01', output=layer, overwrite=True, quiet=True):
        raise RuntimeError('unable to import vectormap ' + fname)

    for f in iglob('proj.*'):
        os.remove(f)

    return layer

def vec2rast(maplayer):
    """Convert vector map to raster of the same name using value of 1.
       Set all null values to be 0.
    """
    grass.run_command('v.to.rast', input=maplayer, output=maplayer, 
        use='val', value='1', quiet=True, overwrite=True)
    grass.run_command('r.null', map=maplayer, null='0', quiet=True)

############# Download map functions using links in config files(luc) ########################
def get_landcover(url):
    # load landcover if one doesn't already exists
    # NOTE: Landcover is only loaded once per scenario. It must
    #   remain outside of buildProbmap incase we use cached probmaps.
    
    landcover = grass.find_file('landcover', element='cell')
    if landcover['name'] == '':
        runlog.p("--download landuse map to landcover raster......")
        site.getURL(url, filename='landcover')
        import_rastermap('landcover', layer='landcover')

        runlog.p("--generate landcoverRedev raster......")
        grass.mapcalc('$redev=if($lu>20 && $lu<25,82, 11)', 
            redev='landcoverRedev', lu='landcover', quiet=True)
    else:
        runlog.p("--local landcover map found, assume landcoverRedev exists......")


def get_nogrowthmaps(urllist):
    """getNoGrowthLayers - downloads 0 or more shapefiles, convert
       them to raster and merge into the noGrowth layers
       To use grass GIS to import vector file requires a new folder
       to be created, and such folder name exist(error and fail otherwise).
       v.in.org
       Thus, each time during import, a tmp folder name is given.
       # To run this, a Temp directory should be created.
    """
    runlog.p("--import nogrowth layers......")
    script = './bin/importNoGrowth'
    logname = './Log/'+ os.path.basename(script)+'.log'
    createdirectorynotexist('./Temp/')

    shplist = []
    for url in urllist:
        layername = get_shapefile(url)
        layername = os.path.basename(layername)
        shplist.append('"%s"' % layername)

    check_call('%s %s > %s 2>&1' % (script, ' '.join(shplist), logname),
        shell=True)

def get_cachedprobmap(url):
    """One scenario only allows one probmap. Once there is a probmap,
       to avoid using cached probmap, users need to create another scenario.
    """
    runlog.p("--check if any probmaps cached......")
    cachedprobmaps = get_rasters(url)
    for probmap in cachedprobmaps:
        runlog.p('***Cached probmap found. Skip building probmap.')
        import_rastermap(probmap, layer=probmap.replace('.gtif', ''))
        return True
    runlog.p("***Cached probmap not found, build it.")
    return False


def get_dem(url):
    """Currently the dem file is downloaded with the startup.py file
       in the portal.leam.illinois.edu/svn/chicagotest.
       TODO: modify leam.luc to set dem file url in config.xml
    """
    d = grass.find_file('demBase', element='cell')
    d['name'] = ''
    if d['name'] == '':
        try:
            runlog.p("--import dem map......")
            site.getURL(url, filename='dem')
            import_rastermap('dem', layer='demBase')
        except Exception:
            runlog.p('--dem driver not found, checking for local version')
            if os.path.exists('./Inputs/dem.gtif'):
                runlog.p('--local dem found, loading as demBase')
                import_rastermap('dem.gtif', layer='demBase')
            else:
                runlog.warn('local dem not found, creating blank demBase')
                grass.mapcalc('demBase=float(0.0)')
    else:
        runlog.p("--local dem map found......")

######################## Functions for main  #################################
def processDriverSets(driver):
    """ Process each Driver Set and generate corresponding probmap.
        @inputs: driver (dict): a Driver Set
                 mode (str): growth or decline
        @outputs:
                 landcoverBase (rast): created in grass
                 landcoverRedev (rast): created in grass
                 return (str, boolean): the year of the earliest Driver Set, isprobmapcached
        The entire processDriverSets should take about 1min.
        TODO: nogrowth has not been used in generating probmap. Should it?
    """
    runlog.p('processing Driver Set %s for year %s' % (driver['title'], driver['year']))

    # get landcover and nogrowth maps for both driver and projection processing
    get_landcover(driver['landuse'])
    get_nogrowthmaps(driver.get('nogrowth', [])) # default=[]

    isprobmapcached = get_cachedprobmap(driver['download'])
    if isprobmapcached:
        return driver['year'], True

    get_dem(driver['dem']) 

    # ywkim added for importing regular roads
    runlog.p("--import road network......")
    shp = get_shapefile(driver['tdm'])
    import_vectormap(shp, layer='otherroads')

    runlog.p("--import empcenters......")
    shp = get_shapefile(driver['empcenters']['empcenter'])
    import_vectormap(shp, layer='empcentersBase')

    runlog.p("--import popcenters......\n")
    shp = get_shapefile(driver['popcenters']['popcenter'])
    import_vectormap(shp, layer='popcentersBase')

    return driver['year'], False # return the startyear, iscachedprobmap


def cacheProbmaps(driverurl):
    runlog.p("--cache probamps......")
    try:
        os.system("zip -j Data/probmaps.zip Data/probmap_res.tif Data/probmap_com.tif")
        site.putProbmapCache(driverurl, "Data/probmaps.zip")
    except Exception:
        runlog.warn("Failed caching probmaps")


def processProjectionSet(projection):
    runlog.p("--import boundary map to be raster......")
    boundary = get_shapefile(projection['layer'])
    import_vectormap(boundary, layer='boundary')
    vec2rast('boundary')

    runlog.p("--import pop_density map to be raster......")
    if projection['pop_density'] != None:
        popdensity = get_shapefile(projection['pop_density'])
        import_vectormap(popdensity, layer='pop_density')
        vec2rast('pop_density')
    else:
        runlog.p("***pop_density not found. Use default pop_density.")

    
    runlog.p("--import emp_density map to be raster......")
    if projection['emp_density'] != None:
        empdensity = get_shapefile(projection['emp_density'])
        import_vectormap(empdensity, layer='emp_density')
        vec2rast('emp_density')
    else:
        runlog.p("***emp_density not found. Use default emp_density.")

    runlog.p("--fetch demand table from website......")
    demandstr = site.getURL(projection['graph']).getvalue()
    return demandstr

def publishResults(title, site, resultsdir):
     
    publishSimMap(title+"_change", site, resultsdir+"/results", 
        '21 blue is residential change and 23 red is commeritial change', nomin=True)
    publishSimMap(title+"_summary", site, resultsdir+"/results",
        'year 0 to year last with color blue to red', nomin=True) 
    publishSimMap(title+"_ppcell", site, resultsdir+"/results",
        'residential population change per cell', nomin=True)
    publishSimMap(title+"_empcell", site, resultsdir+"/results",
        'commertial population change per cell', nomin=True) 
    publishSimMap(title+"_year", site, resultsdir+"/results",
        'year that cell cell has been changed', nomin=True)
    
    # Add nogrowth map or nogrowth_flooding map into the overlayer based on differnt uploaded driverset
    maptitle1 = "sh_nogrowth" 
    maptitle2 = "Area_prone_to_flooding_dissolved"
    if os.path.exists("Inputs/%s" % maptitle2):
        print "find flood map shape file"
         # The same as zip nogrowth file using command line
        os.system("zip -r ./Inputs/%s.zip ./Inputs/%s" % (maptitle2, maptitle2))
    	simmap = "Inputs/%s.zip" % maptitle2 
    	mapfile = "Outputs/%s.map" % maptitle1 
    	url = resultsdir + "/results"    
    	popattrurl = site.putSimMap("%s.zip" % maptitle2, "%s.map" % maptitle1, url,
		simmap_file = open(simmap, "rb"),
		mapfile_file = open(mapfile, "rb"))
    	site.updateSimMap(popattrurl, title=maptitle2, description="nogrowth flooding map")
    else:
        #os.system("cd Inputs && zip sh_nogrowth.zip sh_nogrowth && cd ..")
    	
        os.system("zip -r ./Inputs/sh_nogrowth.zip ./Inputs/sh_nogrowth")
	simmap = "Inputs/%s.zip" % maptitle1 
    	mapfile = "Outputs/%s.map" % maptitle1
    	url = resultsdir + "/results"    
    	popattrurl = site.putSimMap("%s.zip" % maptitle1, "%s.map" % maptitle1, url,
		simmap_file = open(simmap, "rb"),
		mapfile_file = open(mapfile, "rb"))
    	site.updateSimMap(popattrurl, title=maptitle1, description="nogrowth map")
   
  
    ##  Todo: change the result maps' names to be without "title"!
    # zip the results and publish to the website
    # check_call(['zip', 'model_results.zip', 'ppcell.gtif', 'hhcell.gtif',
    #         'empcell.gtif', 'year.gtif', 'change.gtif'])
    # site.putFileURL('model_results.zip', resultsdir, title='Model Results')

def main():    
         
    # The system stdout and stderr will be in /leam/scratch/<scenarioname>/<scenarioname>.log
    jobstart = time.asctime()
    os.environ['PATH'] = ':'.join(['./bin', os.environ.get('BIN', '.'),'/bin', '/usr/bin'])
    configurl, user, password = parseFlags()
    
    print "Parsing configuration file.............\n"
    configfile = get_config(configurl, user, password)
    luc = LUC(configfile)
    print luc.growthmap[0]
    # luc has sorted luc.growthmap(drivers) in year and luc.growth(projections)

    print "Setting up GRASS environment.............\n"
    get_grassfolder(luc.scenario['grass_loc'], user, password)
    grasssetup.grassConfig()
    global grass
    grass = grasssetup.grass
    
    print "Connect to the LEAM storage server............."
    resultsdir = luc.scenario['results']
    print resultsdir, '\n'

    title = luc.scenario['title']
    global site, runlog # run.log will be stored in Log repository
    site = LEAMsite(resultsdir, user=user, passwd=password)
 
    #create runlog file 
    site.createFolder("RunLog", resultsdir)    



    runlog = RunLog(resultsdir+"/runlog", site, initmsg='Scenario ' + title)
    runlog.p('started at '+jobstart)
    
    # creat two folders
    site.createFolder("Details", resultsdir)
    site.createFolder("Results", resultsdir)


    global projectiontable
    projectiontable = ProjTable()
    
    growth = dict(deltapop=[0.0], deltaemp=[0.0])
    if luc.growth: # note growthmap[0]...should change luc, using luc_new
        runlog.h('Processing Growth driver set.............')
        startyear, isprobmapcached = processDriverSets(luc.growthmap[0])
        if not isprobmapcached:
            runlog.h('Building Probability Maps..............')
            runMulticostModel(resultsdir, site, runlog)
            cacheProbmaps(luc.growthmap[0]['url'])            

    if luc.growthmap:
        runlog.h('Processing Growth Projection set........')
        demandstr = processProjectionSet(luc.growth[0])
        genYearChangemap.executeGLUCModel(demandstr, title, runlog)
        runlog.h('Publishing all results..............')
        #wrap the simmap file to Results
        publishResults(title, site, resultsdir+"/results")

if __name__ == "__main__":
    """
    #Code below is used to test publishReults function to add nogrowth map
    title = "scenario160923floodnodensity"
    resultsdir = "http://portal.leam.illinois.edu/stockholm2016/luc/scenarios/scenario160923floodnodensity"
    site = LEAMsite(resultsdir, sys.argv[1], sys.argv[2])
    publishResults(title, site, resultsdir)
    """
    try:
        main()
    # Uncaught or re-raised error from main
    except Exception as e:
        # remove .tif files and save .txt files for debuging the problem.
        os.system('rm ./Data/*.tif ./gluc/Data/* ./bin/glucsrc/*.h ./bin/glucsrc/*.c')
        if 'runlog' in globals():
            runlog.error(str(e))
            runlog.exception('main() exits with exception')
            runlog.error('Scenario Terminated')
            sys.exit(1)

        # runlog has not be initialized, use default error handling
        else:
            raise

    # successful termination
    runlog.h('Scenario Completed Successfully at %s.' % time.asctime())
    os.system('rm -r *') # remove all files to save space. Otherwise, one scenario
                      # will take 20% /dev/dm-0 space. Use 'df' to check space use.
    sys.exit(0) 
     
