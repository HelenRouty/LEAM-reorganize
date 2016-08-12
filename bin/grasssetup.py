#!/usr/bin/env python
import os
import sys
sys.path += ['./bin']
from glob import iglob
import time
# from Utils import extractheader

# GRASSHEADER="./Input/grassheader.txt"
# import subprocess
# from subprocess import check_call

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

def import_rastermap(fname):
    """Import a raster layer into GRASS
    Note that we need a PERMANENT folder in grass folder that has pre-setted projection
    information prepared before importing rastermap.
    @param filename without .gtif postfix
    """
    # proj = grass.read_command('g.proj', flags='wf')
    # with open(os.devnull, 'wb') as FNULL:
    #      check_call(['gdalwarp', '-t_srs', proj, 'Data/landcover.gtif', 'Data/landcover.gtif'], 
    #                 stdout=FNULL, stderr=subprocess.STDOUT, shell=True)

    if grass.find_file(fname)['name']:
         grass.run_command('g.remove', flags='f', rast=fname)
    infilename = './Input/' + fname + '.tif'
    if grass.run_command('r.in.gdal', input=infilename, output=fname,
            overwrite=True, quiet=True):
        raise RuntimeError('unable to import rastermap ' + fname)

def printRegionInfo(fname):
    if grass.run_command('r.info', map=fname):
        raise RuntimeError('unable to print region info ' + fname)

def import_vectormap(layername):
    """Import a vector layer into GRASS. The reion is set to the vector map with 30 meters resolution.
       @param: layername is the input vector files folder and also the imported layer name.
    """
    # remove prior exisiting raster and vector layers
    if grass.run_command('g.remove', rast=layername, vect=layername):
        raise RuntimeError('unable to clear prior raster and vector file: ' + layername)

    # set the region to fit the current vector file with 30 meters resotluion
    if grass.run_command('g.region', flags='d', res=30):
        raise RuntimeError('unable to set region ')

    pathname = './Input/' + layername

    # import vector map
    if grass.run_command('v.in.ogr', flags='o', dsn=pathname,
            snap='0.01', output=layername, overwrite=True, quiet=True):
        raise RuntimeError('unable to import vectormap ' + layername)

def printVectorColumns(layername):
    # print vector map data column names
    if grass.run_command('v.db.connect', map=layername, flags='c'):
        raise RuntimeError('unable to print info of vectormap ' + layername)

def vector2rasterpop1000(layername, column_to_select='TOTAL_POP'):
    """Transform  the TOTAL_POP column value that is larger than 1000 in the vector layer to raster layer.
       @param: layername is the vector layer to be transformed to the raster form of this layer.
       Note that it is required to have "TOTAL_POP" column in the vector file.
    """
    layer1000 = layername + "1000"
    if grass.run_command('v.extract', input=layername, output=layer1000, overwrite=True,
        where='TOTAL_POP>=1000'):
        raise RuntimeError('unable to convert vector to raster: ' + layername)
    if grass.run_command('v.to.rast', input=layer1000, output=layername, overwrite=True,
        use='attr', column=column_to_select):
        raise RuntimeError('unable to convert vector to raster: ' + layername)

def vector2rasterspeed(layername, column_to_select='SPEED'):
    """Transform  the TOTAL_POP column value that is larger than 1000 in the vector layer to raster layer.
       @param: layername is the vector layer to be transformed to the raster form of this layer.
               column_to_select is to select one layer of value to the raster file. The default is to select class type.
    """
    if grass.run_command('v.to.rast', input=layername, output=layername, overwrite=True,
        use='attr', column=column_to_select):
        raise RuntimeError('unable to convert vector to raster: ' + layername)

def export_asciimapnull1(layername):
    """Export a raster layer into asciimap. The output folder is 'Data/'.
       @param: layername is the raster layer name.
    """
    outfilename = 'Data/'+layername+'.txt'
    if grass.run_command('r.out.ascii', input=layername, output=outfilename, null=1):
        raise RuntimeError('unable to export ascii map ' + layername)
    # outfilename = 'Data/'+layername+'.tiff'
    # if grass.run_command('r.out.tiff', input=layername, output=outfilename):
    #     raise RuntimeError('unable to export tiff map ' + layername)    

def ascii2raster(layername):
    filename = './Data/' + layername + '.txt'
    grassheader = extractheader(GRASSHEADER)
    os.system('sed -i -e "1,6d" '+ filename) #delete first 6 lines
    lines = grassheader.rstrip().split('\n') #insert header line by line
    for line in reversed(lines):
        os.system("sed -i 1i\ '" + line+"' " +filename) #insert header to the 1st line
    if grass.run_command('r.in.ascii', input=filename, output=layername):
        raise RuntimeError('unable to read ascii map to raster map ' + layername )

def gencontour(layername, contourname):
    """This process takes about 22sec for one map 
    """
    if grass.run_command('r.contour', input=layername, output=contourname, levels=[3817,5000,6000,7000,9000, 11000, 12000, 13000, 15000, 18000, 23008]):
        raise RuntimeError('unable to generate contour map for ' + layername )

    # print vector map data column names
    if grass.run_command('v.db.connect', map=contourname, flags='c'):
        raise RuntimeError('unable to print info of vectormap ' + contourname)

def vector2rastercat(layername):
    if grass.run_command('v.to.rast', input=layername, output=layername, overwrite=True,
        use='cat'):
        raise RuntimeError('unable to convert vector cat to raster: ' + layername)

def exportraster(layername):
    outfilename = 'Data/'+layername+'.tif'
    if grass.run_command('r.out.gdal', input=layername, output=outfilename, type='UInt16'):
        raise RuntimeError('unable to export raster map ' + layername )

def main():
    grassConfig()

    LANDUSEMAP = 'landuse'
    ROADMAP = 'chicago_road2'
    POPCENTERMAP = 'pop_center'
    EMPCENTERMAP = 'emp_centers5'
    VISIALMAP = 'attrmap-emp-interpolated'
    CONTOURMAP = 'attrmap_pop_contour'

    # # transform raster landuse to ascii map
    # import_rastermap(LANDUSEMAP)
    # export_asciimap(LANDUSEMAP)

    # # transform vector road map to ascii map
    # import_vectormap(ROADMAP)
    # vector2rasterspeed(ROADMAP)
    # export_asciimapnull1(ROADMAP)

    # # transform population centers vector files to ascii map with 2010 population data.
    # import_vectormap(POPCENTERMAP)
    # vector2rasterpop1000(POPCENTERMAP)
    # export_asciimap(POPCENTERMAP)

    # # transform employment centers vector files to ascii map with 2010 population data.
    # import_vectormap(EMPCENTERMAP)
    # vector2rasterpop1000(EMPCENTERMAP)
    # export_asciimap(EMPCENTERMAP)

    # visualize an ascii map to rastermap
    # ascii2raster(VISIALMAP)
    # exportraster(VISIALMAP)

    #start = time.time()
    #gencontour(VISIALMAP, CONTOURMAP)
    #vector2rastercat(CONTOURMAP)
    #print "time to convert raster: ", (time.time()-start)
    #exportraster(CONTOURMAP)
    #print "time to export raster: ", (time.time()-start)

    # vector2raster - overlandTravelTime30
    print "empcentersBase: ---------"
    printVectorColumns("empcentersBase")
    print "ctmpv: --------"
    printVectorColumns("ctmpv")
    print "overlandTravelTime30: ------"
    printVectorColumns("cross")



if __name__ == "__main__":
	main()
