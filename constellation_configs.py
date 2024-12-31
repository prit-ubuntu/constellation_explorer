# Defines the zoom levels for ground tracks
MAXZOOM = 5.5
MIDZOOM = 6.5
MINZOOM = 6
# Defines the radius size for ground tracks
MINRAD = 600
MIDRAD = 700
MAXRAD = 1200
# Defines the min elevations for transits
# http://systemarchitect.mit.edu/docs/delportillo18b.pdf 
MINELEV = 80
MIDELEV = 85
MAXELEV = 87

CONFIGS = {
    "SPIRE" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/LEMUR~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "PLANET" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/SKYSAT~~/OBJECT_NAME/FLOCK~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "SWARM" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/SPACEBEE~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "STARLINK" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/STARLINK~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "ONEWEB" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/ONEWEB~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MIDELEV,
        "_RADIUSLEVELS"  : MIDRAD,
        "_ZOOMLEVELS"    : MIDZOOM },
    "GLOBALSTAR" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/GLOBALSTAR~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MIDELEV,
        "_RADIUSLEVELS"  : MIDRAD,
        "_ZOOMLEVELS"    : MIDZOOM },
    "IRIDIUM" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/IRIDIUM~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "ORBCOMM" : {
        "_URL": "/class/tle_latest/ORDINAL/1/OBJECT_NAME/ORBCOMM~~/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MIDELEV,
        "_RADIUSLEVELS"  : MIDRAD,
        "_ZOOMLEVELS"    : MIDZOOM },
    "AMATUER": {
        "_URL": "/class/tle_latest/favorites/Amateur/ORDINAL/1/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "NAVSTAR (USA)": {
        "_URL": "/class/tle_latest/favorites/Navigation/ORDINAL/1/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MAXELEV,
        "_RADIUSLEVELS"  : MAXRAD,
        "_ZOOMLEVELS"    : MAXZOOM },
    "SPECIAL INTEREST": {
        "_URL": "/class/tle_latest/favorites/Special_Interest/ORDINAL/1/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "WEATHER": {
        "_URL": "/class/tle_latest/favorites/Weather/ORDINAL/1/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    "VISIBLE": {
        "_URL": "/class/tle_latest/favorites/Visible/ORDINAL/1/format/3le/orderby/NORAD_CAT_ID%20asc",
        "_MINELEVATIONS" : MINELEV,
        "_RADIUSLEVELS"  : MINRAD,
        "_ZOOMLEVELS"    : MINZOOM },
    }

ERROR_CODES = {
    "0": "No error.",
    "1": "Mean eccentricity is outside the range 0 ≤ e < 1.",
    "2": "Mean motion has fallen below zero.",
    "3": "Perturbed eccentricity is outside the range 0 ≤ e ≤ 1.",
    "4": "Length of the orbit's semi-latus rectum has fallen below zero.",
    "5": "N/A: Not used anymore.",
    "6": "Orbit has decayed: the computed position is underground.",
}

TLE_GROUP_URL = {
    "Last 30 days' launches": "last-30-days",
    "Space Stations": "stations",
    "Brightest Satellites": "visual",
    "Weather Satellites": "weather", 
    "Disaster Monitoring": "dmc", 
    "Search & Rescue (SARSAT)": "sarsat",
    "Tracking and Data Relay Satellite System (TDRSS)" : "tdrss", 
    "CubeSats": "cubesat",
    "GPS Operational": "gps-ops", 
    "Galileo": "galileo", 
    "Beidou": "beidou",
    "GNSS": "gnss"
}


