#!/usr/local/bin/python
"""
Simple wrappers for interacting with the LEAM plone site.
"""

import sys, os
import re
import urllib2
import os.path as path
from StringIO import StringIO
from mechanize import Browser
from optparse import OptionParser

LEAMSITE = "http://portal.leam.illinois.edu/chicago"

def url_join(*args):
    """Join any arbitrary strings into a forward-slash delimited list.
    Do not strip leading / from first element, nor trailing / from 
    last element.
    """

    if len(args) == 0:
        return ""

    if len(args) == 1:
        return str(args[0])

    else:
        args = [str(arg).replace("\\", "/") for arg in args]

        work = [args[0]]
        for arg in args[1:]:
            if arg.startswith("/"):
                work.append(arg[1:])
            else:
                work.append(arg)

        joined = reduce(os.path.join, work)

    return joined.replace("\\", "/")

def get_filename(rsp):
    """parse the headers from the urllib2 response and return the
    filename from the Content-Disposition field.
    """
    s = rsp.info().getheader('content-disposition')
    fname = re.search(r'filename="([^"]+)"', s).group(1)
    return fname


class LEAMsite:
    
    def __init__(self, site, user, passwd):
        self.site = site
        self.error = False
        self.b = Browser()
        self.b.set_handle_robots(False)

        try:
            self.b.open(site)
        except urllib2.URLError:
            self.error = True
            return

        try:
            # try and log in from the portlet
            self.b.select_form('loginform')
        except:
            # try logging in from the main login page
            self.b.open('/'.join((site,"login_form")))
            self.b.select_form(nr=1)
            
        self.b['__ac_name'] = user
        self.b['__ac_password'] = passwd
        r = self.b.open(self.b.click())

        # plone changes have rendered this inoperable
        # capture the response and look in the content
        # body tag has class with login failure

    def checkURL(self, url):
        """Tries to open a URL and return true if successful (object exists)
        or false if error occurs.  
        """

        try:
            rsp = self.b.open(url)
        except:
            return False

        return True


    def getURL(self, url, data=None, filename=None):
        """Simple interface for retrieving the contents of a URL
           and writing it to a file or returning it as stringIO.
        """
        #sys.stderr.write('getURL %s\n' % url)

        rsp = self.b.open(url, data)

        if filename:
            f = file("./Inputs/"+filename, 'wb') # always write to Input folder
            f.write(rsp.read())
            f.close()
            return None
        else:
            return StringIO(rsp.read())
        

    def putFileURL(self, filename, url, 
                   fileobj=None, title=None, type='text/plain'):
        """Simple interface for uploading a file to a plone site.
           <URL> should be an existing folder on the site and
           <filename> should be a readable file.
        """ 

        #sys.stderr.write('putFileURL %s to %s\n' % (filename,url))
        if not title: title = path.basename(filename)
        if not fileobj: fileobj = open(filename, 'rb')

        self.b.open('/'.join((url,'createObject?type_name=File')))
        self.b.select_form("edit_form")
        self.b['title'] = title
        self.b.add_file(fileobj, type, path.basename(filename))
        # form = self.b.find_control('file_delete')
        # form.value = ["",]

        self.b.submit("form.button.save")
        # r = self.b.open(self.b.click())
        # should check that it worked


    def getFile(self, url, filename=None):
        """ getFile -- gets a file using standard download from Plone site
        url: The URL is pointer to the file on the Plone site
        filename: optional filename where data will be written
        """
        rsp = self.b.open(url_join(url,'at_download/file'))

        if filename:
            f = open(filename, 'wb')
            f.write(rsp.read())
            f.close()
            return None
        else:
            return rsp.read()

    def saveFile(self, url, dir=".", at_download=False):
        """Reads the response from a URL and saves it to a local
        file based on the name provided in the Content-Disposition
        header.  

	    The dir field specifies to the directory where the file will
        be stored.

        If the at_download flag is True then 'at_download/file' will
        be appended the URL.
        """
        if at_download:
            rsp = self.b.open(url_join(url,'at_download/file'))
        else:
            rsp = self.b.open(url)
 
        fname = get_filename(rsp)
	if fname:
            f = open('/'.join([dir, fname]), 'wb')
            f.write(rsp.read())
            f.close()

	return fname

    def putImageURL_old(self, imgfile, url, title=None, type='image/jpg'):
        sys.stderr.write('putImageURL %s to %s\n' % (imgfile,url))
        self.b.open('/'.join((url,'createObject?type_name=Image')))
        self.b.select_form("edit_form")
        if not title: title = path.basename(imgfile)
        self.b['title'] = title
        self.b.add_file(open(imgfile), type, path.basename(imgfile))
        try:
            # doesn't seem necessary but it is required for file upload
            form = self.b.find_control('image_delete')
            form.value = ["",]
            # print "This really does need to happen.."
        except:
            # print "That delete stuff never happens..." 
            pass
        self.b.submit("form.button.save")


    def putImageURL(self, filename, url, 
                   fileobj=None, title=None, type='image/jpg'):
        """Simple interface for uploading a file to a plone site.
           <URL> should be an existing folder on the site and
           <filename> should be a readable file.
        """ 

        #sys.stderr.write('putFileURL %s to %s\n' % (filename,url))
        if not title: title = path.basename(filename)
        if not fileobj: fileobj = open(filename, 'rb')

        self.b.open('/'.join((url,'createObject?type_name=Image')))
        self.b.select_form("edit_form")
        self.b['title'] = title
        self.b.add_file(fileobj, type, path.basename(filename))
        # form = self.b.find_control('file_delete')
        # form.value = ["",]

        self.b.submit("form.button.save")
        # r = self.b.open(self.b.click())
        # should check that it worked


    def putDocument(self, doc, url, title):
        """Creates a new document and add the doc (file-like object) to it."""

        self.b.open('/'.join((url,'createObject?type_name=Document')))
        self.b.select_form("edit_form")

        self.b['title'] = title
        doc.seek(0)
        self.b['text'] = doc.read()

        self.b.submit("form.button.save")
        return self.b.geturl()


    def getDocument(self, url):
       """Returns a string with the text of the current document."""

       self.b.open('/'.join((url,'edit')))
       self.b.select_form("edit_form")

       s = self.b['text']
       self.b.submit("form.button.cancel")
       return s


    def editDocument(self, doc, url, title=None):
       """Replaces the contents of a document"""

       self.b.open('/'.join((url,'edit')))
       self.b.select_form("edit_form")

       # update the title if given
       if title: self.b['title'] = title

       # slightly dangerous approach where we seek first
       # to test for a file-like object.  If exception is
       # thrown then assume doc is a string.
       try:
           doc.seek(0)
           self.b['text'] = doc.read()
       except:
           self.b['text'] = doc

       self.b.submit("form.button.save")
       return self.b.geturl()


    def createFolder(self, folder, url):
        """Creates a folder titled <folder> at the location <url> if 
           it doesn't already exist. Returns the full path of new folder.
        """

        pathurl = '/'.join((url,folder.lower().replace(' ','-')))
        print pathurl
        try:
            self.b.open(pathurl)
        except:
            self.b.open('/'.join((url,'createObject?type_name=Folder')))
            self.b.select_form("edit_form")
            self.b['title'] = folder
            self.b.submit("form.button.save")

        return self.b.geturl()

    def editFolder(self, url, title="", description=""):
        """Edit the basic fields of the Folder.  Mostly useful for 
           setting the title AFTER creating the folder with a reasonable
           short name.
        """
        try:
            self.b.open(url)
        except:
            self.error = True
            return None

        self.b.open(url+'/edit')
        self.b.select_form("edit_form")
        if title:
            self.b['title'] = title
        if description:
            self.b['description'] = description
        self.b.submit("form.button.save")

        return self.b.geturl()

    def deleteFolder(self, url):
        "Deletes folder and all of its contents"

        sys.stderr.write('DELETING folder %s\n' % url)
            
        return

    # Puts SimMaps on to the site
    def putSimMap(self, simmap, mapfile, url,
                  simmap_file=None, mapfile_file=None,
                  title=None, description=None, 
                  trans=.7, details=None, zoom=8):
        """ putSimMap
        Required Input: simmap, mapfile, url
          simmap is a file that contains the desired GIS layer
          mapfile is the standard .map file that maps GIS layer to image
          url - is the full URL to the folder where the SimMap will be stored
        Optional Inputs: simmap_file, mapfile_file, title, trans, details
          simmap_file - file-like object of the simmap if None simmap
                        will be openned and read.
          mapfile_file - file-like object of the mapfile. If None mapfile
                         will be openned and read.
          title - title sting of the SimMap defaults to basename(simmap)
          trans - transparency level
          details - description of SimMap as stored in the details field
        """

        self.b.open('/'.join((url,'createObject?type_name=SimMap')))
        self.b.select_form("edit_form")

        if not simmap_file: simmap_file = open(simmap, 'rb')
        if not mapfile_file: mapfile_file = open(mapfile, 'rb')
        if not title: title = path.splitext(path.basename(simmap))[0]
        self.b['title'] = str(title)
        self.b.add_file(simmap_file, 'application/octet-stream',
                        path.basename(simmap), "simImage_file")
        self.b.add_file(mapfile_file, 'application/octet-stream', 
                        path.basename(mapfile), "mapFile_file")        
        if description: self.b['description'] = str(description)
        self.b['transparency'] = str(trans)
        self.b['zoom'] = str(zoom)
        if details: self.b['details'] = str(details)
        self.b.submit("form.button.save")

        return self.b.geturl()


    def getSimMap(self, url):
        """ return the SimMap metadata

        Gets the metadata associated with SimMap including title,
        description, location, transparency, and zoom.
       = """
        self.b.open(url+'/edit')
        self.b.select_form('edit_form')

        d = dict(
            title = self.b['title'],
            description = self.b['description'],
            details = self.b['details'],
            location = self.b['location'],
            transparency = self.b['Transparency'],
            zoom = self.b['zoom'],
            )
        self.b.submit("form.button.cancel")
        return d

    def updateSimMap(self, url, **kwargs):
        """ update the SimMap metadata
        
        Keywords must match the field names from the edit form exactly,
        extra keywords (or mispelled ones) will be ignored.
        """

        self.b.open(url+'/edit')
        self.b.select_form('edit_form')
        
        for k in kwargs:        
            if k in self.b:
                self.b[k] = str(kwargs[k])

        self.b.submit("form.button.save")


    def getSimMapData(self, url, filename=None):
        """ getSimMapData -- gets the data component of the the SimMap
        url: The URL is pointer to the SimMap on the Plone site
        filename: optional filename where data will be written
        """

        bufsize = 15 * 1024 * 1024

        rsp = self.b.open(url_join(url,'at_download/simImage'))

        if filename:
            f = file(filename, 'wb')
            while 1:
                b = rsp.read(bufsize)
                f.write(b)
                if len(b) < bufsize: break
            f.close()
            return None
        else:
            return StringIO(rsp.read())

       
    def getSimMapMapfile(self, url, filename=None):
        """ getSimMapData -- gets the mapfile component of the the SimMap
        url: The URL is pointer to the SimMap on the Plone site
        filename: optional filename where data will be written
        """

        rsp = self.b.open(url_join(url,'at_download/mapFile'))

        if filename:
            f = file(filename, 'wb')
            f.write(rsp.read())
            f.close()
            return None

        else:
            data = StringIO()
            data.write(rsp.read())
            return data


    def putProbmapCache(self, url, filename):
        """store precomputed probmaps as part of the Driver Set

        This is a temporary method until the REST interface
        is ready.  It's really depricated before it written!
        """

        self.b.open(url+'/edit')
        self.b.select_form('edit_form')

        with open(filename, 'rb') as f:
            self.b.add_file(f, 'application/octet-stream', 
                            path.basename(filename), name='probfile_file')
            self.b.submit("form.button.save")

    # def putAttrmapCache(self, url, filepathbasename, filename):
    #     """store precomputed maps as part of the Driver Set

    #     This is a temporary method until the REST interface
    #     is ready.  It's really depricated before it written!
    #     """

    #     self.b.open(url+'/edit')
    #     self.b.select_form('edit_form')

    #     with open(filename, 'w') as f:
    #         self.b.add_file(f, 'application/octet-stream', 
    #                         path.basename(filepathbasename), name=filename)
    #         self.b.submit("form.button.save")


    # DELETE FUNCTIONS -----------------------------------------
    # These functions delete items from the LEAM Plone sites
    # ----------------------------------------------------------
    def deleteItem(self,fname,url):
        """ deleteItem
        Deletes <fname> from the folder <url>
        """
        print '/'.join((url,fname,'delete_confirmation'))
        print self.b.open('/'.join((url,fname,'delete_confirmation')))
        self.b.select_form(None,None,1)
        print self.b.submit()


# TEST FUNCTIONS ----------------------------------------------
# Command line function tester
# -------------------------------------------------------------
def check_args(args, size):

    if len(args) == size: return
    
    sys.stderr.write('Error: incorrect number of arguments:')
    sys.stderr.write('%d provided %d expected.\n' % (len(args), size))
    sys.stderr.write('args = "%s"\n' % str(args))
    sys.exit(1)

def main():
    usage = '%prog [options] -u/--url <URL>'
    parser = OptionParser(usage=usage, description=__doc__)

    parser.add_option("-u", "--url", metavar="URL", default=None,
       help="<URL> of plone site")
    parser.add_option("-n", "--username", metavar="USERNAME", default='',
       help="<USERNAME> used to authenticate to plone")
    parser.add_option("-p", "--password", metavar="PASSWORD", default='',
       help="<PASSWORD> used to authenticate to plone")

    parser.add_option("-t", "--title", metavar="TITLE", default=None,
       help="<TITLE> for files, images or folders to be added")
    parser.add_option("-d", "--details", metavar="DETAILS", default=None,
       help="<DETAILS> to fill up details section where applicable")

    parser.add_option('--putfolder', dest='mode', 
        action='store_const', const='putfolder',
        help='creates folder in plone (args: <NAME>)')

    parser.add_option('--putfile', dest='mode', 
        action='store_const', const='putfile',
        help='upload file to plone (args: <FILENAME>)')
    parser.add_option('--getfile', dest='mode', 
        action='store_const', const='getfile',
        help='download file from plone (args: <FILENAME>)')

    parser.add_option('--putimage', dest='mode', 
        action='store_const', const='putimage',
        help='upload image to plone (args: <IMAGE>)')
    parser.add_option('--getimage', dest='mode', 
        action='store_const', const='getimage',
        help='download image from plone (args: <IMAGE>)')

    parser.add_option('--putpage', dest='mode', 
        action='store_const', const='putpage',
        help='upload page to plone (args: <FILE>)')
    parser.add_option('--getpage', dest='mode', 
        action='store_const', const='getpage',
        help='download page from plone (args: <FILE>)')
    parser.add_option('--editpage', dest='mode', 
        action='store_const', const='editpage',
        help='replace page on plone (args: <FILE>)')

    parser.add_option('--putsimmap', dest='mode',
        action='store_const', const='putsimmap',
        help='upload simmap to plone (args: <LAYER> <MAPFILE>)')
    parser.add_option('--getsimmapdata', dest='mode',
        action='store_const', const='getsimmapdata',
        help='download SimMap Data from plone (args: <LAYER>)')
    parser.add_option('--getsimmapmapfile', dest='mode',
        action='store_const', const='getsimmapmapfile',
        help='download SimMap MAPFILE from plone (args: <MAPFILE>)')
    parser.add_option("-y", "--transparency", metavar="TRANSPARENCY",
       default='0.7', help="<TRANSPARENCY> on a SimMap")


    (opts, args) = parser.parse_args()

    if opts.url:
        site = LEAMsite(opts.url, opts.username, opts.password)
    else:
        sys.stderr.write('Error: URL must be specified.\n\n')
        parser.print_help()
        sys.exit(1)


    if opts.mode == 'putfolder':
        check_args(args, 1)
        site.createFolder(opts.title, args[0])

    elif opts.mode == 'putfile':
        check_args(args, 1)
        site.putFileURL(args[0], opts.url, title=opts.title)

    elif opts.mode == 'getfile':
        check_args(args, 1)
        site.getFile(opts.url, filename=args[0])

    elif opts.mode == 'putimage':
        check_args(args, 1)
        site.putImageURL(args[0], opts.url, title=opts.title)
    
    elif opts.mode == 'getimage':
        check_args(args, 1)
        site.putImage(opts.url, args[0])

    elif opts.mode == 'putpage':
        check_args(args, 1)
        site.putDocument(args[0], opts.url, title=opts.title)

    elif opts.mode == 'getpage':
        check_args(args, 1)
        s = site.getDocument(opts.url)
        f = open(args[0], 'w')
        f.write(s)
        f.close()

    elif opts.mode == 'editpage':
        check_args(args, 1)
        f = open(args[0])
        s = site.editDocument(f, opts.url, opts.title)
        f.close()

    elif opts.mode == 'putsimmap':
        check_args(args, 2)
        site.putSimMap(args[0], args[1], opts.url, 
             title=opts.title, trans=opts.transparency, details=opts.details)
        
    elif opts.mode == 'getsimmapdata':
        check_args(args, 1)
        site.getSimMapData(opts.url, args[0])

    elif opts.mode == 'getsimmapmapfile':
        check_args(args, 1)
        site.getSimMapMapfile(opts.url, args[0])
       
    else:
        sys.stderr.write('Error: unknown mode')
        sys.exit(1)


if __name__ == "__main__":
    main()

