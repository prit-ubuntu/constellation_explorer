# Defines the zoom levels for ground tracks
MAXZOOM = 5.5
MIDZOOM = 6.5
MINZOOM = 7
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
    'SPIRE':    {   
                    '_MINELEVATIONS' : MINELEV,
                    '_MAXALTITUDES'  : 600,
                    '_RADIUSLEVELS'  : MINRAD,
                    '_ZOOMLEVELS'    : MINZOOM      
                },
    'PLANET':   {   
                    '_MINELEVATIONS' : MINELEV,
                    '_MAXALTITUDES'  : 700,
                    '_RADIUSLEVELS'  : MINRAD,
                    '_ZOOMLEVELS'    : MINZOOM      
                },
    'STARLINK': {   
                    '_MINELEVATIONS' : MINELEV,
                    '_MAXALTITUDES'  : 600,
                    '_RADIUSLEVELS'  : MINRAD,
                    '_ZOOMLEVELS'    : MINZOOM      
                },
    'SWARM':    {   
                    '_MINELEVATIONS' : MINELEV,
                    '_MAXALTITUDES'  : 600,
                    '_RADIUSLEVELS'  : MINRAD,
                    '_ZOOMLEVELS'    : MINZOOM      
                },
    'ONEWEB':   {   
                    '_MINELEVATIONS' : MIDELEV,
                    '_MAXALTITUDES'  : 1200,
                    '_RADIUSLEVELS'  : MIDRAD,
                    '_ZOOMLEVELS'    : MIDZOOM      
                },
    'GALILEO':  {   
                    '_MINELEVATIONS' : MAXELEV,
                    '_MAXALTITUDES'  : 33000,
                    '_RADIUSLEVELS'  : MAXRAD,
                    '_ZOOMLEVELS'    : MAXZOOM     
                },
    'BEIDOU':   {   
                    '_MINELEVATIONS' : MAXELEV,
                    '_MAXALTITUDES'  : 21000,
                    '_RADIUSLEVELS'  : MAXRAD,
                    '_ZOOMLEVELS'    : MAXZOOM     
                },
    'GNSS':     {   
                    '_MINELEVATIONS' : MAXELEV,
                    '_MAXALTITUDES'  : 20000,
                    '_RADIUSLEVELS'  : MAXRAD,
                    '_ZOOMLEVELS'    : MAXZOOM      
                },
    'NOAA':     {   
                    '_MINELEVATIONS' : MAXELEV,
                    '_MAXALTITUDES'  : 35800,
                    '_RADIUSLEVELS'  : MINRAD,
                    '_ZOOMLEVELS'    : MINZOOM      
                },
    'IRIDIUM':  {   
                    '_MINELEVATIONS' : MINELEV,
                    '_MAXALTITUDES'  : 800,
                    '_RADIUSLEVELS'  : MIDRAD,
                    '_ZOOMLEVELS'    : MIDZOOM      
                },
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
    "Space Stations": "stations",
    "Brightest Satellites": "visual",
    "Russian ASAT Test Debris (COSMOS 1408)": "1982-092",
    "Chinese ASAT Test Debris (FENGYUN 1C)": "1999-025",
    "IRIDIUM 33 Debris" : "iridium-33-debris",
    "COSMOS 2251 Debris" : "cosmos-2251-debris",
    "Weather Satellites": "weather", 
    "Disaster Monitoring": "dmc", 
    "Search & Rescue (SARSAT)": "sarsat",
    "Tracking and Data Relay Satellite System (TDRSS)" : "tdrss", 
    "CubeSats": "cubesat",
    "Molniya": "molniya", 
    "GPS Operational": "gps-ops", 
    "Spire": "spire", 
    "Planet": "planet", 
    "Starlink": "starlink", 
    "Swarm": "swarm", 
    "OneWeb": "oneweb", 
    "Galileo": "galileo", 
    "Beidou": "beidou",
    "GNSS": "gnss", 
    "Iridium": "iridium", 
    "NOAA": "noaa"
}


