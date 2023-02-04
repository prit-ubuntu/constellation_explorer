import streamlit as st
import pandas as pd
from pytz import timezone
from timezonefinder import TimezoneFinder
import numpy as np
from datetime import (datetime as dt, time, timedelta)

import warnings
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning) 

LOCATIONS = {'BOULDER': (40.015, -105.27),
             'SAN FRANCISCO': (37.78, -122.41),
             'NEW YORK': (40.73, -74.0),
             'MUMBAI': (19.08, 72.88),
             'LONDON': (51.5, -0.13),
             'SHANGHAI': (31.23, 121.47),
             'CAPE TOWN': (-33.92, 18.42),
             'RIO DE JIANERIO': (-22.91, -43.1),
             'SYDNEY': (-33.87, 151.21),
             'MOSCOW': (55.76, 37.62),
             'TOKYO': (35.68, 139.65),
             'RAJKOT': (22.30, 70.80),
             'REYKJAVIK': (64.15, 21.94),
             'CAIRO': (30.04, 31.24),
             'SANTIAGO': (-33.45, -70.67),
             'MEXICO CITY': (19.43, -99.13),
             'ATHENS': (37.98, 23.73),
             'PARIS': (48.86, 2.35),
             'ROME': (41.90, 12.50), 
             'CORVALLIS': (44.56, -123.26), 
             'PORTLAND': (45.51, -122.68), 
             'SANTA CRUZ': (36.97, -122.03), 
             'WEST LAFAYETTE': (40.43, -86.91), 
             'ANN ARBOR': (42.28, -83.74),
             'LITTLE ROCK': (34.74, -92.28),
             'CUSTOM LOCATION': (10.00, 10.00)
            }

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
        self.selected_tz = 'UTC' # string
        self.date_range = None # TUPLE of start/stop datetime objects (with timezone)
        self.timerangeset = False

    def initialize_location_services(self, choice):
        self.initialized = True
        self.selected_loc = choice #string

    def initialize_time_services(self, dateChoice):
        if dateChoice[1] > dateChoice[0]:
            self.date_range = dateChoice
            self.start_datestr = dateChoice[0]
            self.end_datestr = dateChoice[1]
            self.timerangeset = True
        return None

    def _update_timezone(self):
        tf = TimezoneFinder()
        tzName = tf.timezone_at(lat=self.selected_position[0],lng=self.selected_position[1])
        if tzName is not None:
            self.selected_tz = tzName
        else:
            self.initialized = False
            st.sidebar.error('Unable to find timezone based on provided lat/long. Please update the lat/long to ensure timezone is supported.')
