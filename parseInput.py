import os
import sys
import time
sys.path += ['./bin']
from optparse import OptionParser
import requests

from luc_config import LUC

scenariosurl = 'http://portal.leam.illinois.edu/chicago/luc/scenarios/'

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

def main():
    os.environ['PATH'] = ':'.join(['./bin', os.environ.get('BIN', '.'),'/bin', '/usr/bin'])
    projectid, user, password = parseFlags()
    configfile = get_config(projectid, user, password)

    print "Parsing configuration file.............\n"
    luc = LUC(configfile)

    # print "Setting up GRASS environment.............\n"


if __name__ == "__main__":
    main()    