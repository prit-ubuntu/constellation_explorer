# json response schema definition for tle_latest class
# ['ORDINAL', 'COMMENT', 'ORIGINATOR', 'NORAD_CAT_ID', 'OBJECT_NAME',
#  'OBJECT_TYPE', 'CLASSIFICATION_TYPE', 'INTLDES', 'EPOCH',
#  'EPOCH_MICROSECONDS', 'MEAN_MOTION', 'ECCENTRICITY', 'INCLINATION',
#  'RA_OF_ASC_NODE', 'ARG_OF_PERICENTER', 'MEAN_ANOMALY', 'EPHEMERIS_TYPE',
#  'ELEMENT_SET_NO', 'REV_AT_EPOCH', 'BSTAR', 'MEAN_MOTION_DOT',
#  'MEAN_MOTION_DDOT', 'FILE', 'TLE_LINE0', 'TLE_LINE1', 'TLE_LINE2',
#  'OBJECT_ID', 'OBJECT_NUMBER', 'SEMIMAJOR_AXIS', 'PERIOD', 'APOGEE',
#  'PERIGEE', 'DECAYED']

requestDict = {
    "STARLINK" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/STARLINK~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "ONEWEB" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/ONEWEB~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "SPIRE" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/LEMUR~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "PLANET" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/SKYSAT~~/OBJECT_NAME/FLOCK~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "SWARM" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/SPACEBEE~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "GEO" : "/class/tle_latest/MEAN_MOTION/0.99--1.01/ORDINAL/1/ECCENTRICITY/%3C0.01/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "MEO" : "/class/tle_latest/MEAN_MOTION/1.8--2.39/ORDINAL/1/ECCENTRICITY/<0.25/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "LEO" : "/class/tle_latest/MEAN_MOTION/>11.25/ORDINAL/1/ECCENTRICITY/<0.25/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "HEO" : "/class/tle_latest/ORDINAL/1/ECCENTRICITY/>0.25/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "GLOBALSTAR" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/GLOBALSTAR~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "INMARSAT" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/INMARSAT~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "INTELSAT" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/INTELSAT~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "IRIDIUM" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/IRIDIUM~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "ORBCOMM" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/ORBCOMM~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "HUMAN_SPACEFLIGHT": "/class/tle_latest/favorites/Human_Spaceflight/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "AMATUER": "/class/tle_latest/favorites/Amateur/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "NAVIGATION": "/class/tle_latest/favorites/Navigation/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "SPECIAL_INTEREST": "/class/tle_latest/favorites/Special_Interest/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "WEATHER": "/class/tle_latest/favorites/Weather/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "VISIBLE": "/class/tle_latest/favorites/Visible/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "BRIGHT_GEO": "/class/tle_latest/favorites/brightgeo/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "ALL_OBJECTS" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc"
}

statItems = {
    "Launch Year": "LAUNCH_YEAR",
    "Altitude (km)" : "ALTITUDE", 
    "Inclination (deg)" : "INCLINATION",
    "Eccentricity" : "ECCENTRICITY",
    "RAAN (deg)" : "RA_OF_ASC_NODE", 
    "Arg. of Perigee (deg)" : "ARG_OF_PERICENTER", 
    "Orbital Revolution Number" : "REV_AT_EPOCH", 
    "NORAD ID": "NORAD_CAT_ID", 
    "BSTAR": "BSTAR"
}

groupbyItems = {
    "Launch Year" : "LAUNCH_YEAR",
    "Decay vs Active" : "STATUS", 
    "Classification" : "CLASSIFICATION_TYPE"
}

