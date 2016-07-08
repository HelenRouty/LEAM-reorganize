
def genSimMap(spatialcode, classColorCondlist, filename):
    """This function generates simMap: the meta data for maps projected on google map
       for SimMap add-on for Plone.
       @inputs: 1. spatial code: a code string for each UTM Zone.
                For example, Chicago in UTM Zone 16N: 26916.
                [http://sdmdataaccess.nrcs.usda.gov/SpatialReferenceHelp.htm]
                2. classColorCondlist: a string triplet list of (classname, condition, RGB)
                Sample condition can be "> 50". RGB colors is represented as a string with 
                R, G, B numerical values seperated by a space.
                3. filename: the map name of the simMap file to output.
       @output: the simMap file with filename and postfix .map into ./Outputs folder.
    """
    # get header and footer from simMapheader.txt
    with open ("./Inputs/simMapheader.txt") as f:
    	lines = f.readlines()
    header = lines[:-2]
    footer = lines[-2:]

    # generate strings for each class color
    classcolor_list = []
    for classname, cond, color in classColorCondlist:
        classcolor_list.append ('\
    CLASS\n\
      NAME "class%s"\n\
      EXPRESSION (%s)\n\
      STYLE\n\
        COLOR %s\n\
      END\n\
    END\n\n' % (classname, cond, color))

    # generate projection location
    projection = '\
    PROJECTION\n\
      "init=epsg:%s"\n\
    END\n' % (spatialcode)

    classcolor_list.append(projection)

    # write strings to filename.map
    outdata = "".join(header + classcolor_list + footer)
    outfilename = "./Outputs/"+ filename + ".map"
    with open(outfilename, "w") as f:
    	f.writelines(outdata)

def main():
	genSimMap("26916", [("0",  "[pixel] == 0","0 77 168"),
		                # ("1",  "([pixel] >     0) && ([pixel]<=   100)"," 46  70 255"),
		                # ("2",  "([pixel] >   100) && ([pixel]<=   300)"," 56 116 255"),
		                # ("3",  "([pixel] >   300) && ([pixel]<=   500)"," 56 169 255"),
		                # ("4",  "([pixel] >   500) && ([pixel]<=  1000)"," 41 219 255"),
		                # ("5",  "([pixel] >  1000) && ([pixel]<=  2000)"," 64 255 239"),
		                # ("6",  "([pixel] >  2000) && ([pixel]<=  3000)","138 255 190"),
		                # ("7",  "([pixel] >  3000) && ([pixel]<=  5000)","182 255 143"),
		                # ("8",  "([pixel] >  5000) && ([pixel]<=  8000)","218 255  97"),
		                # ("9",  "([pixel] >  8000) && ([pixel]<= 10000)","248 255  38"),
		                # ("10", "([pixel] > 10000) && ([pixel]<= 15000)","255 255   0"),
		                # ("11", "([pixel] > 15000) && ([pixel]<= 20000)","255 179   0"),
		                # ("12", "([pixel] > 20000) && ([pixel]<= 25000)","255 132   0"),
		                # ("13", "([pixel] > 25000) && ([pixel]<= 50000)","255  81   0"),
		                # ("14", " [pixel]>  50000                      ","255   0   0"),
                       ], "pop_grav_attr")

if __name__ == '__main__':
     main()