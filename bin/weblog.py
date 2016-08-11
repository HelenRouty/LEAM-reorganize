import logging
from StringIO import StringIO
from Utils import createdirectorynotexist

class RunLog:
    """Utility class that wraps the standard python logging facility
    and promotes some messages to the log maintained on portal site.
    """
    def __init__(self, resultsdir, site, initmsg=''):
        self.logger = self._init_logger(__name__)
        self.log = StringIO()
        self.site = site

        if initmsg:
            self.log.write('<h2 class="runlog">'+initmsg+'</h2>\n')
        else:
            self.log.write('<h2 class="runlog">Run Started</h2>\n')
        try:
            self.logdoc = self.site.putDocument(self.log, resultsdir, 'Run Log')
        except:
            print "FormNotFoundError in Runlog. Possibly wrong user and password, or wrong url.\n"
            raise

    def _init_logger(self, name, level=logging.DEBUG, fname='./Log/run.log'):
        logger = logging.getLogger(name)
        logger.setLevel(level)

        createdirectorynotexist(fname)
        handler = logging.FileHandler(fname, mode='w')
        handler.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def h(self, s):
        self.logger.info('>>> '+s)
        self.log.write('<h2 class="runlog">'+s+'</h2>\n')
        self.site.editDocument(self.log, self.logdoc)
        print s

    def p(self, s):
        self.logger.info(s)
        self.log.write('<p class="runlog">'+s+'</p>\n')
        self.site.editDocument(self.log, self.logdoc)
        print s

    def warn(self, s):
        self.logger.warn(s)
        self.log.write('<h2 class="runlog-warn">Warning</h2>\n')
        self.log.write('<p class="runlog-warn">' + s + '</p>\n')
        self.site.editDocument(self.log, self.logdoc)
        print s

    def error(self, s):
        self.logger.error(s)
        self.log.write('<h2 class="runlog-err">Error Detected</h2>\n')
        self.log.write('<p class="runlog-err">' + s + '</p>\n')
        self.site.editDocument(self.log, self.logdoc)
        print s

    def exception(self, s):
         self.logger.exception(s)
         print s

    def debug(self, s):
        self.logger.debug(s)
        print s