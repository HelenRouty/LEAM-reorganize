
################### genSimMap.py && multicostModel.py ###############
NUMCOLORS = 15
CHICAGOREGIONCODE = "26916"
SIMMAPHEADER = "./Inputs/simMapheader.txt"

######################### multicostModel.py #########################

##ROADS WEIGHT##
W_STATERD=float(3000)
W_COUNTY=float(10)
W_ROAD=float(0)
W_RAMP=float(1500)
W_INTERSECT=float(500)

##PROBMAP WEIGHT##
WEIGHTS = {
'pop_res':1.5,
'pop_com':2.0,
'transport_res':0.8,
'transport_com':0.9,
'emp_res':1.0,
'emp_com':1.0,
}

##PROBMAP COMPONENTS##
COMSCORELIST = [('pop'      , 'pop_com'      ),
                ('emp'      , 'emp_com'      ),
                ('transport', 'transport_com')]
RESSCORELIST = [('pop'      , 'pop_res'      ),
                ('emp'      , 'emp_res'      ),
                ('transport', 'transport_res')]
COSTSCORELIST= [('forest'  , 'forest'       ),
                ('water'    , 'water'        ),
                ('slope'    , 'slope'        )]

###CENTER LAYER NAMES###
EMPCENTERS = 'empcentersBase'
#EMPCENTERS = 'emp_centers4_47_98' # Note that '-' is not valid filename
POPCENTERS = 'popcentersBase'

GRAPHS="./SFA"

##BUFFER SIZE##
# interstates buffer to generate cross = 60
# water and forest buffer = 30,60,90,120,150,180,210,240,270,300,330,360

######################### genYearChangemap.py #########################
DEMANDGRAPH ='gluc/Data/demand.graphs'