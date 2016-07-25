class ProjTable:
    """A utility class used to track target and actual projections.
    Once the model run is complete the results can be posted to the
    portal.
    """

    def __init__(self):
        self.period = {}
        self.pop = []
        self.emp = []

    def years(self, projid, mode, start, end):
        """store start and end date for each projection"""

        self.period[projid] = (int(start), int(end))


    def population(self, projid, mode, taract, data):
        """update population projection information

        Args:
          projid (str): short name of projection (no spaces, etc)
          mode (str): 'growth', 'decline' or 'regional'
          taract (str): 'target' or 'actual' projection
          data (list): projection values
        """ 
        self.pop.append([projid, mode, taract, 'population',] + \
                [str(x) for x in data])

    def employment(self, projid, mode, taract, data):
        """update employment projection information

        Args:
          projid (str): short name of projection (no spaces, etc)
          mode (str): 'growth', 'decline' or 'regional'
          taract (str): 'target' or 'actual' projection
          data (list): projection values
        """ 

        self.emp.append([projid, mode, taract, 'employment',] + \
                [str(x) for x in data])

    def write_csv(self, filename=''):
        """return CSV formatted string"""

        start = min([x[0] for x in self.period.values()])
        end = max([x[1] for x in self.period.values()])
        ystr = ','.join(['','','','year'] + 
                        [str(y) for y in range(int(start),int(end)+1)])
        
        records = [ystr,] + [','.join(r) for r in self.pop] \
               + [''] + [','.join(r) for r in  self.emp] + ['']
        table = '\n'.join(records)

        if filename:
            with open(filename, 'wb') as f:
                f.write(table)

        return table