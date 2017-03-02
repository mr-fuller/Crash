import arcpy, os
from datetime import datetime

# Intersection polygon file/location
IntersectionFeatures = [Location of layer containing buffered intersections]

# Segment polygon file/location
SegmentFeatures = [Location of layer containing buffered segments]

# Input parameters
GCATfile = arcpy.GetParameterAsText(0)  # user input for text file of crash location data from GCAT
GDBspot = arcpy.GetParameterAsText(1)  # user input location for gdb and result excel tables
fatalwt = float(arcpy.GetParameterAsText(2))  # user input weight for fatal crashes
seriouswt = float(arcpy.GetParameterAsText(3))  # user input weight for serious crashes
nonseriouswt = float(arcpy.GetParameterAsText(4))  # user input weight for nonserious crashes
possiblewt = float(arcpy.GetParameterAsText(5))  # user input weight for possible crashes
IntersectionThreshold = arcpy.GetParameterAsText(6)  # user input number of crashes to qualify an intersection as high crash
SegmentThreshold = arcpy.GetParameterAsText(7)  # User input number of crashes to qualify a segment as high crash

# create geodatabase
TimeDate = datetime.now()
TimeDateStr = "CrashLocations" + TimeDate.strftime('%Y%m%d%H%M')
outputGDB = arcpy.CreateFileGDB_management(GDBspot, TimeDateStr)

# convert GCAT txt file to gdb table and add to map
NewTable = arcpy.TableToTable_conversion(GCATfile, outputGDB, "GCAT_LUCWOO_nofreeways")

# display xy data and export to new feature class
PointFile = arcpy.MakeXYEventLayer_management(NewTable, "ODOT_LONGITUDE_NBR", "ODOT_LATITUDE_NBR", "GCAT_LUCWOO_xy",
                                              arcpy.SpatialReference("NAD 1983"))
# dict of count fields and queries
dict = {'fatalities_Count':"FATALITIES_NBR<>0",
        'incapac_inj_count': "Incapac_injuries_NBR<>0 and fatalities_nbr=0",
        'non_incapac_inj_count':"non_incapac_injuries_NBR<>0 and fatalities_nbr=0 and incapac_injuries_nbr=0",
        'possible_inj_count':"possible_injuries_nbr<>0 and FATALITIES_NBR=0 and non_incapac_injuries_nbr=0 and incapac_injuries_nbr=0"
        }
        
# add and populate fields for point layer
for key in dict:
    arcpy.AddField_management(PointFile,key,"LONG")
    arcpy.SelectLayerByAttribute_management(PointFile, "NEW_SELECTION", dict[key])
    arcpy.CalculateField_management(PointFile, key, 1)
    arcpy.SelectLayerByAttribute_management(PointFile, "Switch_selection")
    arcpy.CalculateField_management(PointFile, key, 0)

# Clear Selected Features
arcpy.SelectLayerByAttribute_management(PointFile, "clear_selection")

PointFeatures = arcpy.FeatureClassToFeatureClass_conversion(PointFile, outputGDB, "GCAT_LUCWOO_xy_points_" + TimeDateStr)

# dict of feature type and corresponding threshold and feature class
ftype = {'Intersection':[IntersectionThreshold, IntersectionFeatures],'Segment':[SegmentThreshold, SegmentFeatures]}

# field map and merge rules

for f in ftype:

    # Create a new fieldmappings and add the two input feature classes.
    fieldmappings = arcpy.FieldMappings()
    fieldmappings.addTable(ftype[f][1])
    fieldmappings.addTable(PointFeatures)

    # list of fields to map 
    flds = ["fatalities_count", "incapac_inj_count","non_incapac_inj_count","possible_inj_count"]
    for fld in flds:

        FieldIndex = fieldmappings.findFieldMapIndex(fld)
        fldmap = fieldmappings.getFieldMap(FieldIndex)
        # Get the output field's properties as a field object
        outputFld = fldmap.outputField
        # Rename the field and pass the updated field object back into the field map
        outputFld.name = "sum_" + fld
        outputFld.aliasName = "sum_" + fld
        fldmap.outputField = outputFld
        # Set the merge rule to sum and then replace the old fieldmaps in the mappings object
        # with the updated ones
        fldmap.mergeRule = "sum"
        fieldmappings.replaceFieldMap(FieldIndex, fldmap)

    # Run the Spatial Join tool, using the defaults for the join operation and join type
    loc = os.path.join(GDBspot, TimeDateStr + ".gdb\\" + f + "Join")
    Join = arcpy.SpatialJoin_analysis(ftype[f][1], PointFeatures,loc,"Join_one_to_one", "keep_all", fieldmappings)
    
    # Add fields for calculating Property Damage Only crashes and Equivalent Property Damage Only Index
    arcpy.AddField_management(Join, "PDO_", "LONG")
    arcpy.AddField_management(Join, "EPDO_Index", "DOUBLE")
    
    # list of fields to use in update cursor operation 
    CursorFlds = ['PDO_',
                  'EPDO_Index',
                  'Join_Count',
                  'sum_fatalities_count',
                  'sum_incapac_inj_count',
                  'sum_non_incapac_inj_count',
                  'sum_possible_inj_count'
                  ]

    # determine PDO  and EPDO Index/Rate
    with arcpy.da.UpdateCursor(Join, CursorFlds) as cursor:
        for row in cursor:
            try:
                #Calculate PDO
                row[0] = row[2] - int(row[3]) - int(row[4]) - int(row[5]) - int(row[6])
            except:
                # set PDO to 0 if Join count = 0 and other fields are NULL
                row[0] = 0
            try:
                # Calculate EPDO Index
                row[1] = (float(row[3]) * fatalwt + float(row[4]) * seriouswt + float(row[5]) * nonseriouswt + float(
                    row[6]) * possiblewt + float(row[0])) / float(row[2]) 
            except:
                # set EPDO Index to 0 if Join count = 0 and other fields are NULL
                row[1] = 0
            cursor.updateRow(row)

    # list of fields to keep (will depend on layer schema)
    keepFlds = ['OBJECTID',
                'Shape',
                'Shape_Area',
                'Shape_Length',
                'Name',
                'Join_Count',
                'sum_fatalities_count',
                'sum_incapac_inj_count',
                'sum_non_incapac_inj_count',
                'sum_possible_inj_count',
                'PDO_',
                'EPDO_Index',
                'Fed_Aid_Buffer_Segments_2_Name',
                'Length_ft']
    
    dropFlds = [x.name for x in arcpy.ListFields(Join) if x.name not in keepFlds]
    # delete fields
    arcpy.DeleteField_management(Join, dropFlds)

    # select high crash locations
    JoinLayer = arcpy.MakeFeatureLayer_management(Join,os.path.join(GDBspot, TimeDateStr + ".gdb\\" + f + "JoinLayer"))
    arcpy.SelectLayerByAttribute_management(JoinLayer, "NEW_SELECTION", "Join_Count >=" + ftype[f][0])

    # export locations to Excel
    arcpy.TableToExcel_conversion(JoinLayer, os.path.join(GDBspot, f + "_Scores" + TimeDateStr + ".xls"))
    arcpy.SelectLayerByAttribute_management(JoinLayer, "CLEAR_SELECTION")
