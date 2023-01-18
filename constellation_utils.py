import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import pandas as pd
import numpy as np

# SETUP LIST OF ALL CONSTELLATIONS
# http://systemarchitect.mit.edu/docs/delportillo18b.pdf 
_MINELEVATIONS = {'SPIRE': 80, 
                  'PLANET': 80, 
                  'STARLINK': 80, 
                  'SWARM': 80, 
                  'ONEWEB': 80, 
                  'GALILEO': 80, 
                  'BEIDOU': 80, 
                  'GNSS': 80,
                  'NOAA': 80, 
                  'IRIDIUM': 80} 

# Names of all constellations
CONSTELLATIONS = list(_MINELEVATIONS.keys())
_URL = 'http://celestrak.com/NORAD/elements/'

DEBUG = False
VERBOSE = False

class TransitEvent():
    '''
    Object that contains info about a transit event
    '''
    def __init__(self, rise_time, culminate_time, set_time, sat_name):
        self.rise = rise_time
        self.culminate = culminate_time
        self.set = set_time
        self.asset = sat_name

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
                event = TransitEvent(rise_events[i], culmination_events[i], setting_events[i], self.satrec_object.name)
                self.events.append(event)
        return None

    def get_events_df(self, tz):
        # utility for converting class into pd df 
        df = pd.DataFrame.from_records([ev.to_dict(tz) for ev in self.events])
        return df

    def drop_events(self):
        # used for callback when location / time range changes, we do not want to remember events
        self.events = []
    
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

    def generateHistogram(self):
        # TODO: GENERATE HISTOGRAM FUNCTION
        # values = sat_times.groupby([sat_times["DATETIME"].dt.day, sat_times["DATETIME"].dt.hour]).count()
        # df2 = values[['SAT NAME']]
        # test = self.schedule.copy()
        # st.dataframe(test, use_container_width=True)
        # test_group = test.groupby('CULMINATE TIME', as_index=False)
        # fig = px.histogram(test, x="CULMINATE", y="SET", color="ASSET", marginal="rug", hover_data=test.columns)
        # df = px.data.tips()
        # st.dataframe(df, use_container_width=True)
        # fig = px.histogram(df, x="total_bill", y="tip", color="sex", marginal="rug",
        #                 hover_data=df.columns)
        # st.plotly_chart(fig, theme="streamlit")
        return None



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