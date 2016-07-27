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
        print "  *%s found, downloading as %s..." % (fname, zipfname)
        z = ZipFile(zipfname)
    except BadZipfile:
        print "  *bad zip file"
        return [fname, ]
    # TODO fix error handling ???
    except:
        print "  *empty zip file"
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
            print "     get_raster: ", outfname
            with open(outfname, 'wb') as f:
                f.write(z.read(fname))
    os.remove(zipfname)
    print "     remove %s" % zipfname
    return rasters


def get_shapefile(url, downloaddir='./Inputs'):
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
    runlog.debug('import_rastermap %s' % fname)
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

############# Download map functions using links in config files(luc) ########################
def get_landcover(url):
    # load landcover if one doesn't already exists
    # NOTE: Landcover is only loaded once per scenario. It must
    #   remain outside of buildProbmap incase we use cached probmaps.
    
    landcover = grass.find_file('landcover', element='cell')
    if landcover['name'] == '':
        print "--download landuse map to landcover raster............."
        site.getURL(url, filename='landcover')
        import_rastermap('landcover', layer='landcover')

        print "--generate landcoverRedev raster............."
        grass.mapcalc('$redev=if($lu>20 && $lu<25,82, 11)', 
            redev='landcoverRedev', lu='landcover', quiet=True)
    else:
        print "--local landcover map found, assume landcoverRedev exists............."


def get_nogrowthmaps(urllist):
    """getNoGrowthLayers - downloads 0 or more shapefiles, convert
       them to raster and merge into the noGrowth layers
    """
    print "--importing nogrowth layers............."
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
    print "--checking if any probmaps cached............."
    cachedprobmaps = get_rasters(url)
    for probmap in cachedprobmaps:
        print '  *Cached probmap found. Skip building probmap.'
        import_rastermap(probmap, layer=probmap.replace('.gtif', ''))
        return True
    print "  *cached probmap not found, build it."
    return False


def get_dem(url):
    # load DEM layer only once and assume it never changes
    # TODO: merge get_landcover, get_dem...
    # TODO: upload dem file to the web server
    d = grass.find_file('demBase', element='cell')
    if d['name'] == '':
        try:
            print "--import dem map............."
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
    else:
        print "--local dem map found............."


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
    isprobmapcached = False # Just for test
    if isprobmapcached:
        return driver['year'], True

    get_dem(driver['dem'])

    # ywkim added for importing regular roads
    print "--importing road network.............."
    shp = get_shapefile(driver['tdm'])
    import_vectormap(shp, layer='otherroads')

    print "--importing empcenters.............."
    shp = get_shapefile(driver['empcenters']['empcenter'])
    layer = import_vectormap(shp, layer='empcentersBase')

    print "--importing popcenters.............\n"
    shp = get_shapefile(driver['popcenters']['popcenter'])
    layer = import_vectormap(shp, layer='popcentersBase')

    return driver['year'], False # return the startyear,


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

    # print "Setting up GRASS environment.............\n"
    # get_grassfolder(luc.scenario['grass_loc'], user, password)
    # grasssetup.grassConfig()
    # global grass
    # grass = grasssetup.grass
    
    # print "Connect to the LEAM file storage server............."
    resultsdir = luc.scenario['results']
    print resultsdir, '\n'
    title = luc.scenario['title']
    # global site, runlog # run.log will be stored in Log repository
    # site = LEAMsite(resultsdir, user=user, passwd=password)
    # runlog = RunLog(resultsdir, site, initmsg='Scenario ' + title)
    # runlog.p('started at '+jobstart)

    # global projectiontable
    # projectiontable = ProjTable()
    
    # growth = dict(deltapop=[0.0], deltaemp=[0.0])
    if luc.growth: # note growthmap[0]...should change luc, using luc_new
        # print 'Processing Growth driver set.............'
        # startyear, isprobmapcached = processDriverSets(luc.growthmap[0])
        isprobmapcached = False # for test only
        if not isprobmapcached:
            print "Building Probability Maps.............."
            cmd = 'python bin/multicostModel.py %s %s %s > ./Log/probmap.log 2>&1' \
            % (resultsdir, user, password)
            check_call(cmd.split())












if __name__ == "__main__":
    main()    