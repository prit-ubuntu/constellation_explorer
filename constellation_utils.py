import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import pandas as pd
import numpy as np
import pydeck as pdk
import plotly.figure_factory as ff
import plotly.express as px

# SETUP LIST OF ALL CONSTELLATIONS
# http://systemarchitect.mit.edu/docs/delportillo18b.pdf 
_MINELEVATIONS = {'SPIRE': 80, 
                  'PLANET': 80, 
                  'STARLINK': 80, 
                  'SWARM': 80,
                  'ONEWEB': 85, 
                  'GALILEO': 87, 
                  'BEIDOU': 87, 
                  'GNSS': 87,
                  'NOAA': 87, 
                  'IRIDIUM': 80} 

_MAXALTITUDES = {'SPIRE': 600, 
                 'PLANET': 630, 
                 'STARLINK': 550, 
                 'SWARM': 530, 
                 'ONEWEB': 1200, 
                 'GALILEO': 33000, 
                 'BEIDOU': 21150, 
                 'GNSS': 20000,
                 'NOAA': 35790, 
                 'IRIDIUM': 780} 

MAXZOOM = 5.5
MIDZOOM = 6.5
MINZOOM = 7

MINRAD = 600
MIDRAD = 700
MAXRAD = 1200
CITYRAD = 1600

_RADIUSLEVELS = {'SPIRE': MINRAD, 
                 'PLANET': MINRAD, 
                 'STARLINK': MINRAD, 
                 'SWARM': MINRAD, 
                 'ONEWEB': MIDRAD, 
                 'GALILEO': MAXRAD, 
                 'BEIDOU': MAXRAD, 
                 'GNSS': MAXRAD,
                 'NOAA': MINRAD, 
                 'IRIDIUM': MIDRAD} 

_ZOOMLEVELS = {'SPIRE': MINZOOM, 
               'PLANET': MINZOOM, 
               'STARLINK': MINZOOM, 
               'SWARM': MINZOOM, 
               'ONEWEB': MIDZOOM, 
               'GALILEO': MAXZOOM, 
               'BEIDOU': MAXZOOM, 
               'GNSS': MAXZOOM,
               'NOAA': MINZOOM, 
               'IRIDIUM': MIDZOOM} 

# Names of all constellations
CONSTELLATIONS = list(_MINELEVATIONS.keys())
_URL = 'http://celestrak.com/NORAD/elements/'

DEBUG = False
VERBOSE = False

NUM_TRACK = 50
KM_BIN_SIZE = 100

class TransitEvent():
    '''
    Object that contains info about a transit event
    '''
    def __init__(self, rise_time, culminate_time, set_time, sat_name, satrecObj):
        self.rise = rise_time # ts objects
        self.culminate = culminate_time # ts objects
        self.set = set_time # ts objects
        self.asset = sat_name
        self.geo_position = None # array of geocentric [x,y,z] (km) from rise to set 
        self.latlon = None # array of [lat,lon] (deg)

        if isinstance(satrecObj, EarthSatellite):
            self.satrec = satrecObj
        else:
            self.satrec = None
            print('did not add esatrec object!')

    def get_ephem(self):
        
        res = False

        ts = load.timescale()
        ts_range = ts.linspace(self.rise, self.set, NUM_TRACK)

        geo_pos = np.zeros([NUM_TRACK, 3])
        lat_lon = np.zeros([NUM_TRACK, 2])

        for id, time in enumerate(ts_range):
            geocentric = self.satrec.at(time)
            lat, lon = wgs84.latlon_of(geocentric)
            geo_pos[id] = np.array([geocentric.position.km[0], geocentric.position.km[1], geocentric.position.km[2]])
            lat_lon[id] = np.array([lat.degrees, lon.degrees])
        
        self.geo_position = geo_pos
        self.latlon = lat_lon
        res = True

        return res

    def to_dict(self, tz):
        # utility for converting object into reportable data in given tz
        return {
            'RISE': self.rise.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'CULMINATE': self.culminate.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'SET': self.set.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'ASSET': self.asset
        }

    def __str__(self):
        return f"\n  Rise: {self.rise.utc_iso()} | Culminate: {self.culminate.utc_iso()} | Set: {self.set.utc_iso()}"

class SatelliteMember(EarthSatellite):
    '''
    Object that contains info about a satellite object and transit events
    '''
    def __init__(self, st_object):
        self.satrec_object = st_object # see above for attrs
        self.events = []

    def add_events(self, times, events):
        rise_events, culmination_events, setting_events = times[np.where(events==0)], times[np.where(events==1)], times[np.where(events==2)]
        # only add event if entire event is complete
        if len(rise_events) == len(culmination_events) == len(setting_events):
            for i in range(len(rise_events)):
                event = TransitEvent(rise_events[i], culmination_events[i], setting_events[i], self.satrec_object.name, self.satrec_object)
                self.events.append(event)
        return None

    def get_events_df(self, tz):
        # utility for converting class into pd df 
        df = pd.DataFrame.from_records([ev.to_dict(tz) for ev in self.events])
        return df

    def drop_events(self):
        # used for callback when location / time range changes, we do not want to remember events
        self.events = []

    def create_ephemeris(self):
        res = False
        for event in self.events: 
            res = event.get_ephem()
        return res

    def __str__(self):
        str_title = f"{self.satrec_object.name} | Epoch: {self.satrec_object.epoch.utc_iso()} | Events: {len(self.events)}"
        for event in self.events:
            str_title = f"{str_title} {event}"
        return str_title

class SatConstellation(object):
    '''
    Object that contains all relevant information and methods for constellation!
    '''
    def __init__(self, constellation):
        self.constellation = constellation
        self._debug = DEBUG
        self._cache_debug = DEBUG
        self.initialized = False
        self.num_passes = 0
        self.unique_passes = 0
        # download satellite data
        self.satellites = self.get_sats()
        # To be filled by generated sched
        self.schedule = pd.DataFrame()

    def get_sats(self):
        '''
        @brief Take in constellation name and get all relevant information

        @return writes EarthSatellite object to class, 
        see more at: https://rhodesmill.org/skyfield/api-satellites.html#skyfield.sgp4lib.EarthSatellite 
        '''

        def query_url():
            # check that desired constellation is valid
            if self.constellation.upper() not in CONSTELLATIONS:
                raise ValueError('Could not find constellation!')
            if self._cache_debug:
                print('Queried new data!')
            url = f'{_URL}{self.constellation.lower()}.txt'
            try:
                satellites = load.tle_file(url)
                return satellites # EarthSatellite
            except Exception as e:
                st.error('Failed to get constellation data!')
        
        member_satellites = []
        satellites = query_url()
        for sat in satellites:
            member_satellites.append(SatelliteMember(sat))
        self.initialized = True
        return member_satellites

    def generatePasses(self, usrLocObject):
        '''!
        @brief  Generate the passes of a specific constellation over a specified location and time range.

        @param usrLocObject    TUPLE of latitude and longitude        

        @return passes      generate passes vector
        '''

        def findPasses():
            for sat in self.satellites:
                times, events = sat.satrec_object.find_events(self.cityLatLon, self.time[0], self.time[1], _MINELEVATIONS[self.constellation])
                if len(events) > 0:
                    sat.add_events(times, events)
                if DEBUG and VERBOSE: 
                    print(sat)

        # check if initialized
        if not self.initialized:
            return False

        position = usrLocObject.selected_position
        dateRange = usrLocObject.date_range
        ts = load.timescale()
        self.cityLatLon = wgs84.latlon(position[0], position[1])
        self.time = (ts.from_datetime(dateRange[0]), ts.from_datetime(dateRange[1]))
        self.tz = dateRange[0].tzinfo
        findPasses()
        return None

    def getSchedule(self):
        '''
        @return passes      PANDAS df [Satellite Name, Time of Rise (string), Culminate (string), Set (string)(Datetime object)]
        '''
        df_list = []
        for sat in self.satellites:
            df_list.append(sat.get_events_df(self.tz))
        passes_df = pd.concat(df_list)
        # update class attributes
        self.num_passes = len(passes_df)
        if self.num_passes:
            self.unique_passes = len(passes_df['ASSET'].unique())
            self.schedule = passes_df
        return self.schedule.copy()

    def dropEvents(self):
        '''
        @return None, updates the constellation object with NO events
        '''
        if DEBUG:
            print('Dropped all events for satellites since time range / location was changed!')
        for sat in self.satellites:
            sat.drop_events()
        return None


    def showStats(self):

        tab1, tab2 = st.tabs(["Ground Tracks", "SMA Distribution"])
        with tab1:
            gTrack = self.generateGroundTracks()
            st.pydeck_chart(gTrack)
        with tab2:
            smaHist = self.showSMADist()
            st.plotly_chart(smaHist, theme="streamlit")

        return None


    def generateGroundTracks(self):
        lat_list, lon_list, asset_list = [], [], []
        for sat in self.satellites:
            if sat.create_ephemeris():
                for event in sat.events:
                    for node in event.latlon:
                        lat_list.append(node[0])
                        lon_list.append(node[1])
                        asset_list.append(event.asset)

        chart_data = pd.DataFrame({"lat": lat_list, "lon": lon_list, "asset": asset_list})

        # Simple implementation
        # st.map(chart_data)
        viewState = pdk.ViewState(latitude=self.cityLatLon.latitude.degrees, 
                                  longitude=self.cityLatLon.longitude.degrees,
                                  zoom=_ZOOMLEVELS[self.constellation], pitch=0)

        layer_1 = pdk.Layer('ScatterplotLayer', data=chart_data, get_position='[lon, lat]',
                           get_color=[150, 249, 123], get_radius=_RADIUSLEVELS[self.constellation], pickable=True, auto_highlight=True)

        r = pdk.Deck(map_style=None, initial_view_state=viewState, layers=[layer_1])
        return r

    def showSMADist(self):

        a_mean_list = []
        name_list = []
        launch_year = []
        for sat in self.satellites:
            try:
                alt = (sat.satrec_object.model.am - 1) * sat.satrec_object.model.radiusearthkm
                # will need to include this sanity check for adding satellite objects
                if sat.satrec_object.model.error == 0 and alt > 0 and alt < 2*_MAXALTITUDES[self.constellation]:
                    a_mean_list.append(alt)
                    name_list.append(sat.satrec_object.name)
                    launch_year.append(f"'{sat.satrec_object.model.intldesg[0:2]}")
                else:
                    if DEBUG: print(f'model with error code #{sat.satrec_object.model.error}, dropping value...')
            except:
                print(type(alt))
                print(sat.satrec_object.model.error)
                print(f'Could not get mean SMA for {sat.satrec_object.name}')

        df_to_plot = pd.DataFrame({'meanSMA (km)': a_mean_list, 'Asset': name_list, 'Launch Year': launch_year})
        num_bins = int((max(a_mean_list) - min(a_mean_list)) / KM_BIN_SIZE)
        # "Mean Semi-major Axis (km)"
        fig = px.histogram(df_to_plot, x="meanSMA (km)", color="Launch Year", marginal="rug", hover_data=df_to_plot.columns)


        if DEBUG:
            print(f"Plotting {len(a_mean_list)} SMAs out of {len(self.satellites)}!")
            print(f"Using {num_bins} bins.")

        return fig



# Complex pydeck plot implementation
# Assign a color based on attraction_type
# color_lookup = pdk.data_utils.assign_random_colors(chart_data['asset'])
# Data now has an RGB color by asset type
# chart_data['color'] = chart_data.apply(lambda row: color_lookup.get(row['asset']), axis=1)
# layer = pdk.Layer('ScatterplotLayer', data=chart_data, get_position='[lon, lat]',
#                   get_color='color', get_radius=600, pickable=True, auto_highlight=True)
# Label datapoints with asset names
# text_layer = pdk.Layer(
#     type='TextLayer',
#     id='text-layer',
#     data=chart_data,
#     pickable=True,
#     get_position='[lon, lat]',
#     get_text='tooltip',
#     get_color='color',
#     # billboard=False,
#     get_size=12,
#     # get_angle=0,
#     # # Note that string constants in pydeck are explicitly passed as strings
#     # # This distinguishes them from columns in a data set
#     # get_text_anchor='"middle"',
#     # get_alignment_baseline='"center"'
# )
# my_tooltip = {"text": f"{chart_data['tooltip']}"}

# class SATREC_OBJECT():
#     'name': 'FLOCK 3R-1', 
#     'model': <sgp4.wrapper.Satrec object at 0x7f8a5908d810>, 
#     'epoch': <Time tt=2459868.2175259604>, 
#     'target': -143747, 
#     'vector_name': 'EarthSatellite', 
#     'center_name': '399 EARTH'

# class SATREC_OBJECT.model():
#     satellite.model.Om              
#     satellite.model.em              
#     satellite.model.j3oj2           
#     satellite.model.nm              
#     satellite.model.sgp4_array(
#     satellite.model.a               
#     satellite.model.ephtype         
#     satellite.model.j4              
#     satellite.model.no              
#     satellite.model.sgp4_tsince(
#     satellite.model.alta            
#     satellite.model.epochdays       
#     satellite.model.jdsatepoch      
#     satellite.model.no_kozai        
#     satellite.model.sgp4init(
#     satellite.model.altp            
#     satellite.model.epochyr         
#     satellite.model.jdsatepochF     
#     satellite.model.nodedot         
#     satellite.model.t
#     satellite.model.am              
#     satellite.model.error           
#     satellite.model.mdot            
#     satellite.model.nodeo           
#     satellite.model.tumin
#     satellite.model.argpdot         
#     satellite.model.gsto            
#     satellite.model.method          
#     satellite.model.om              
#     satellite.model.twoline2rv(
#     satellite.model.argpo           
#     satellite.model.im              
#     satellite.model.mm              
#     satellite.model.operationmode   
#     satellite.model.xke
#     satellite.model.bstar           
#     satellite.model.inclo           
#     satellite.model.mo              
#     satellite.model.radiusearthkm   
#     satellite.model.classification  
#     satellite.model.intldesg        
#     satellite.model.mu              
#     satellite.model.revnum          
#     satellite.model.ecco            
#     satellite.model.j2              
#     satellite.model.nddot           
#     satellite.model.satnum          
#     satellite.model.elnum           
#     satellite.model.j3              
#     satellite.model.ndot            
#     satellite.model.sgp4(