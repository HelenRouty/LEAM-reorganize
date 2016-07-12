This is trying to break the original LEAM codes to pieces and reorganize for more advanced automation.

-----------
Update:

**Data Analysis**

1. multicostModel.py: 
   * generate pop_grav_attr.txt, emp_grav_attr.txt,
   pop_cost.txt, and emp_cost.txt in ./Data by calling cities.py.
   Note: codes in cities.py and multicostModel.py are learned
   from original LEAM codes.
   * `python multicostModel.py`

2. dataanalysis.py: 
   * generate res/com frequency vs. attractivenss & travelcost
   over population centers or employment centers in ./Data/analysis
   * `python dataanalysis.py <attrbasketnum> <costbasketnum> -c <pop/emp>`

**Automate Quantile Color Map Scale**

1. multicostModel.py:
  *  generate .tif maps in ./Data

2. genSimMap.py:
   * generate .map files for each .tif maps in ./Outputs for the quantile color

3. connectLEAMsite.py:
   * upload .tif with its .map to the plone website.
   * `python connectLEAMsite.py <username> <password>


:smile: This is so cool!
--------------------


