import streamlit as st
import pandas as pd
from tzwhere import tzwhere
from pytz import timezone, all_timezones
import numpy as np
from datetime import (datetime as dt, time, timedelta)

import warnings
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning) 

LOCATIONS = {'SAN FRANCISCO': (37.78, -122.41),
                'BOULDER': (40.015, -105.27),
                'RAJKOT': (22.30, 70.80),
                'NEW YORK': (40.71, -74.0),
                'MUMBAI': (19.08, 72.88),
                'LONDON': (51.5, -0.13),
                'SHANGHAI': (31.23, 121.47),
                'CAPE TOWN': (-33.92, 18.42),
                'RIO DE JIANERIO': (-22.91, -43.1),
                'SYDNEY': (-33.87, 151.21),
                'MOSCOW': (55.76, 37.62),
                'TOKYO': (35.68, 139.65),
                'REYKJAVIK': (64.15, 21.94),
                'CAIRO': (30.04, 31.24),
                'SANTIAGO': (-33.45, -70.67),
                'MEXICO CITY': (19.43, -99.13),
                'ATHENS': (37.98, 23.73),
                'PARIS': (48.86, 2.35),
                'ROME': (41.90, 12.50), 
                'CORVALLIS (GO BEAVS!)': (44.56, -123.26), 
                'PORTLAND': (45.51, -122.68), 
                'SANTA CRUZ': (36.97, -122.03), 
                'WEST LAFAYETTE (GO BOILERS!)': (40.43, -86.91), 
                'ANN ARBOR (GO BLUE!)': (42.28, -83.74),
                'CUSTOM LOCATION': (10.00, 10.00)
                }

DATERANGE_DELTA_DAYS = 1

class UserLocation(object):
    '''
    Object that contains all relevant information and methods for lat / long and cities!
    '''
    def __init__(self):
        self.locations_dict = LOCATIONS
        self.locations_list = self.locations_dict.keys()
        self.initialized = False
        self.selected_loc = None # string
        self.selected_position = None # TUPLE of latitude and longitude  
        self.selected_tz = None # string
        self.date_range = None # TUPLE of start/stop datetime objects (with timezone)

    def initialize_location_services(self, choice):
        self.initialized = True
        self.selected_loc = choice #string
        
        state = False
        if self.selected_loc != "CUSTOM LOCATION":
            state = True
        self._update_lat_long_map(state)

    def _update_lat_long_map(self, disp_state):
        c1, c2 = st.columns(2)
        with c1:
            lat = st.sidebar.number_input('Latitude', min_value= -90.0, max_value= 90.0, value=self.locations_dict[self.selected_loc][0], disabled=disp_state)
        with c2:
            lon = st.sidebar.number_input('Longitude', min_value= -180.0, max_value=180.0, value=self.locations_dict[self.selected_loc][1], disabled=disp_state)
        
        self.selected_position = (lat, lon)
        self._update_timezone()

        st.sidebar.map(data=pd.DataFrame({'lat': lat, 'lon': lon}, index=[0]), zoom=5, use_container_width=True)

    def _update_timezone(self):
        
        tz = tzwhere.tzwhere()
        tzName = tz.tzNameAt(self.selected_position[0],self.selected_position[1])
        self.selected_tz = tzName

        if tzName is not None:
            st.sidebar.write('Timezone: ',tzName)
            # get current datetime in timezone
            currentDate = dt.now(timezone(self.selected_tz))    
            endDate = currentDate+timedelta(days=DATERANGE_DELTA_DAYS)
            self.date_range = (currentDate, endDate)
            self.start_datestr = currentDate.strftime("%Y-%m-%d %H:%M:%S")
            self.end_datestr = endDate.strftime("%Y-%m-%d %H:%M:%S")
            
        else:
            self.initialized = False
            st.sidebar.error('Please update the loc / lat / long to ensure timezone is supported.')
