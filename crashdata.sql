

--add geometry column
alter table gcat_luc_woo_2011to2017 add column geom geometry;

--change empty fields to nulls in lat/long columns
update gcat_luc_woo_2011to2017 set odot_longitude_nbr = null where odot_longitude_nbr = '';
update gcat_luc_woo_2011to2017 set odot_latitude_nbr = null where odot_latitude_nbr = '';

--cast lat/long fields as float not text
alter table gcat_luc_woo_2011to2017 alter column odot_latitude_nbr type double precision using odot_latitude_nbr::double precision;
alter table gcat_luc_woo_2011to2017 alter column odot_longitude_nbr type double precision using odot_longitude_nbr::double precision;

--create geometry column from points
update gcat_luc_woo_2011to2017 set geom = ST_MakePoint(odot_longitude_nbr, odot_latitude_nbr);

--update srid?
--create geometry column from linear referencing info?


