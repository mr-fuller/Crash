--batch file of GDAL commands to load data into postgres


--load csv data from GCAT into Postgres; 2011 to 2017 crashes for Lucas and Wood County
ogr2ogr -f "PostgreSQL" PG:"host=localhost user=user dbname=dbname password=password" "[path]\20171004-1411-gcat-results.csv" -nln "gcat_luc_woo_2011to2017"

--load other pertinent files from filegdb
