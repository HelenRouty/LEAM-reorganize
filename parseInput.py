import os
import sys
import time
sys.path += ['./bin']
from optparse import OptionParser
import requests
import subprocess
from subprocess import call
from subprocess import check_call

from luc_config import LUC
import grasssetup
from leamsite import LEAMsite
from weblog import RunLog
from projectiontable import ProjTable

scenariosurl = 'http://portal.leam.illinois.edu/chicago/luc/scenarios/'

######################## Basic Setups and Helper functions #################################
def parseFlags():
    """Three optional arguments required: projectid, user, and password
    """
    usage = "Usage: %prog [options] arg"
    parser = OptionParser(usage=usage, version='%prog')
    parser.add_option('-P', '--projectid', help='projectid')
    parser.add_option('-U', '--user', default=None,
        help='Portal user name (or PORTAL_USER environmental var)')
    parser.add_option('-X', '--password', default=None,
        help='Portal password (or PORTAL_PASSWORD environmental var)')

    (options, args) = parser.parse_args()

    user = options.user or os.environ.get('PORTAL_USER', '')
    password = options.password or os.environ.get('PORTAL_PASSWORD', '')
    if not user or not password:
        sys.stderr.write('User and password information is required. '
                'Please set using -U <username> and -X <password> '
                'on command line or using environmental variables.\n')
        exit(1)

    if not options.projectid:
        sys.stderr.write('Project id (scenario id) is required. '
            'Please set using -P <projectid> on command line.\n')
        exit(1)

    return options.projectid, options.user, options.password


def get_config(projectid, user, password, configfile='config.xml'):
    """get the configuration from any one of multiple sources
 
    Args:
      uri (str): URL or file name
      user (str): portal user 
      password (str): portal password
      fname (str): name of the config file to be written
    """

    if os.path.exists(configfile):
        return configfile

    projecturl = scenariosurl + projectid + "/getConfig"
    print projecturl

    try: 
        r = requests.get(projecturl, auth=(user, password))
        r.raise_for_status()
        config = r.text
    except:
        e = sys.exc_info()[0]
        print ("Error: Cannot access %s's configuration file in url %s. %s"
                % (projectid, projecturl, e))
        exit(1)
    
    with open(configfile, 'w') as f:
        f.write(config)

    return configfile


def get_grassfolder(url, user, password, fname='grass.zip'):
    """download an empty GRASS folder to the current repository
       @inputs: uri (str): URL for download
                user (str): portal user
                password (str): portal password
                fname (str): tmp name for the GRASS location
        TODO: upload grass folder to the server
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


def get_rasters(url):
    """Download file and handle nonexist file.
       If not exist, an empty list returned. Hack...
       TODO: more elegent solution
    """
    try:
        fname = site.saveFile(url)
        z = ZipFile(fname)
    except BadZipfile:
        return [fname, ]
    # TODO fix error handling ???
    except:
        return []

    rasters = []
    for fname in z.namelist():
        if fname.endswith('/'):
            continue
        else:
            fname = os.path.basename(fname)
            rasters.append(fname)
            with open(fname, 'wb') as f:
                f.write(z.read(fname))
    return rasters


def get_shapefile(url):
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
            if fname.endswith('.shp'):
                shapefile = fname
            with open(fname, 'wb') as f:
                content = z.read(zname)
                f.write(content)

    if not shapefile:
        raise RuntimeError('%s did not contain a shapefile' % url)

    return shapefile

############# Download map functions using links in config files(luc) ########################
def get_landcover(url):
    # load landcover if one doesn't already exists
    # NOTE: Landcover is only loaded once per scenario. It must
    #   remain outside of buildProbmap incase we use cached probmaps.
    landcover = grass.find_file('landcoverBase', element='cell')
    if landcover['name'] == '':
        print " ---- download landuse map to landcoverBase raster.............\n"
        site.getURL(url, filename='landcover')
        import_rastermap('landcover', layer='landcoverBase')

        print " ---- generate landcoverRedev raster.............\n"
        grass.mapcalc('$redev=if($lu>20 && $lu<25,82, 11)', 
            redev='landcoverRedev', lu='landcoverBase', quiet=True)


def get_nogrowthmaps(urllist):
    """getNoGrowthLayers - downloads 0 or more shapefiles, convert
       them to raster and merge into the noGrowth layers
    """
    print " -- importing no growth layers.............\n"
    script = './bin/importNoGrowth'
    logname = './Log/'+ os.path.basename(script)+'.log'

    shplist = []
    for url in urllist:
        shplist.append('"%s"' % get_shapefile(url))

    check_call('%s %s > %s 2>&1' % (script, ' '.join(shplist), logname),
        shell=True)


def get_cachedprobmap(url):
    """One scenario only allows one probmap. Once there is a probmap,
       to avoid using cached probmap, users need to create another scenario.
    """
    cachedprobmaps = get_rasters()
    for probmap in cachedprobmaps:
        print '---- cached probmap found: ' + probmap
        import_rastermap(probmap, layer=probmap.replace('.gtif', ''))
        return True
    return False


def get_dem(url):
    # load DEM layer only once and assume it never changes
    # TODO: merge get_landcover, get_dem...
    # TODO: upload dem file to the web server
    d = grass.find_file('demBase', element='cell')
    if d['name'] == '':
        try:
            print " ---- import dem map.............\n"
            site.getURL(url, filename='dem')
            import_rastermap('dem', layer='demBase')
        except Exception:
            runlog.warn('dem driver not found, checking for local version')
            if os.path.exists('dem.zip'):
                runlog.warn('local demo found, loading as demBase')
                check_call('unzip dem.zip', shell=True)
                import_rastermap('dem.gtif', layer='demBase')
            else:
                runlog.warn('local dem not found, creating blank demBase')
                grass.mapcalc('demBase=float(0.0)')


def processDriverSets(driver):
    """ Process each Driver Set and generate corresponding probmap.
        @inputs: driver (dict): a Driver Set
                 mode (str): growth or decline
        @outputs:
                 landcoverBase (rast): created in grass
                 landcoverRedev (rast): created in grass
                 return (str): the year of the earliest Driver Set
        TODO: nogrowth has not been used in generating probmap. Should it?
    """
    runlog.p('processing Driver Set %s for year %s' % (driver['title'], driver['year']))

    # get landcover and nogrowth maps for both driver and projection processing
    get_landcover(driver['landuse'])
    get_nogrowthmaps(driver.get('nogrowth', default=[]))

    isprobmapcached = get_cachedprobmap(driver['download'])
    if isprobmapcached:
        return driver['year']

    get_dem(driver['dem'])

    # ywkim added for importing regular roads
    print " -- importing road network..............\n"
    shp = get_shapefile(driver['tdm'])
    import_vectormap(shp, layer='otherroads')

    print " -- importing empcenters..............\n"
    shp = get_shapefile(driver['empcenters']['empcenter'])
    layer = import_vectormap(shp, layer='empcentersBase')

    print " -- importing popcenters.............\n"
    shp = get_shapefile(driver['popcenters']['popcenter'])
    layer = import_vectormap(shp, layer='popcentersBase')

    return driver['year'] # return the startyear


def main():
    jobstart = time.asctime()
    os.environ['PATH'] = ':'.join(['./bin', os.environ.get('BIN', '.'),'/bin', '/usr/bin'])
    projectid, user, password = parseFlags()
    
    print "Parsing configuration file.............\n"
    configfile = get_config(projectid, user, password)
    # luc = LUC(configfile) #for luc_config_new.py
    with open(configfile) as f:
        config = f.read()
    luc = LUC(config)
    print luc.growthmap[0]
    #luc has sorted luc.growthmap(drivers) in year and luc.growth(projections)

    print "Setting up GRASS environment.............\n"
    get_grassfolder(luc.scenario['grass_loc'], user, password)
    grasssetup.grassConfig()
    global grass
    grass = grasssetup.grass
    
    print "Connect to the LEAM file storage server.............\n"
    resultsdir = luc.scenario['results']
    title = luc.scenario['title']
    global site, runlog # run.log will be stored in Log repository
    site = LEAMsite(resultsdir, user=user, passwd=password)
    runlog = RunLog(resultsdir, site, initmsg='Scenario ' + title)
    runlog.p('started at '+jobstart)

    global projectiontable
    projectiontable = ProjTable()
    
    growth = dict(deltapop=[0.0], deltaemp=[0.0])
    if luc.growth: # note growthmap[0]...should change luc, using luc_new
        print 'Processing Growth driver set.............\n'
        startyear = processDriverSets(luc.growthmap[0], 'growth')
        
        print "Building Probability Maps..............\n"
        cmd = 'python bin/multicostModel.py %s %s empcentersBase popcentersBase' % (resultdir, site)
        check_call(cmd.split())












if __name__ == "__main__":
    main()    