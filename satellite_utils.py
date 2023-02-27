import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import pandas as pd
import numpy as np
import pydeck as pdk
from skyfield.api import utc
from skyfield.positionlib import Geocentric
from skyfield.timelib import Time as SkyfieldTime
import constellation_configs as cc

NUM_TRACK = 500
DEBUG = False

DT_FORMAT = '%b %d, %Y %H:%M:%S'

class StateVector(object):
    '''
    Stores state geoposition object with times
    '''

    def __init__(self, time, geoposition):

        self.epoch = None # SkyfieldTime time object
        self.geoposition = None # Geocentric position object

        if isinstance(time, SkyfieldTime):
            self.epoch = time
        else:
            st.exception(f'State vector needs a SkyfieldTime object, got something else: {type(time)}!')
            raise TypeError
        
        if isinstance(geoposition, Geocentric):
            self.geoposition = geoposition
        else:
            st.exception(f'State vector needs a Geocentric object, got something else: {type(geoposition)}!')
            raise TypeError

    def latlong(self):
        lat, lon = wgs84.latlon_of(self.geoposition)
        return [lat.degrees, lon.degrees]

    def sunlitStatus(self):
        eph = load('de421.bsp')
        return self.geoposition.is_sunlit(eph)
    
    def gcrsPosition(self):
        x, y, z = self.geoposition.position.km[0], self.geoposition.position.km[1], self.geoposition.position.km[2]
        return [x, y, z]


class SatelliteEphemeris(StateVector):
    '''
    Object that contains positonal information about satellites
    '''
    def __init__(self, start_time, end_time, satrecObj):
        self.timerange = [start_time, end_time]
        self.state_vectors = None # list of State vectors
        self.ephem_populated = False # to be initialised by init_states()
        if isinstance(satrecObj, EarthSatellite):
            self.satrec = satrecObj
            self.ephem_populated = self.init_states() # bool to indicate if ephem is generated
        else:
            st.exception(f'Ephemeris needs a satrec object to compute state vectors, got something else: {type(satrecObj)}!')
            raise TypeError

    def init_states(self):
        '''
        initializes self.state_vectors with a list of StateVector objects within self.timerange
        '''
        res = False
        ts = load.timescale()
        try:
            ts_range = ts.linspace(self.timerange[0], self.timerange[1], NUM_TRACK)
            self.state_vectors = [StateVector(time, self.satrec.at(time)) for time in ts_range]
            res = True
        except Exception as e:
            st.exception(f"Failed to initilize state vectors, got exception: {e}!")
        finally:
            return res

    def __getTimesList(self, format=DT_FORMAT):
        '''
        returns a list of time strings for all state vector epochs
        '''
        return [vector.epoch.utc_strftime(format) for vector in self.state_vectors]
    
    def __getLatLongList(self):
        '''
        returns a tuple of (lat list, lon list) for all state vectors
        '''
        lat_lon_list = [vector.latlong() for vector in self.state_vectors]
        lat, lon = map(list, zip(*lat_lon_list))
        return tuple([lat, lon])

    def __getSunlitColorList(self):
        '''
        returns a list of colors for all state vectors, yellow means is sunlit
        '''
        # Color yellow in sunlight and dark_blue in eclipse
        dark_blue = [102, 102, 255]
        yellow = [255, 255, 0]
        list_lit = [vector.sunlitStatus() for vector in self.state_vectors]
        color_list = [yellow if is_sunlit else dark_blue for is_sunlit in list_lit]

        # Color starting and ending points differently
        green_for_start = [0, 255, 0]
        red_for_end = [255, 0, 0]
        color_list[0] = green_for_start
        color_list[-1] = red_for_end

        return color_list
    
    def __getPosList(self):
        '''
        returns a tuple of (x, y, z GCRS pos in km) for all state vectors
        '''
        xyz_list = [vector.gcrsPosition() for vector in self.state_vectors]
        x_pos, y_pos, z_pos = map(list, zip(*xyz_list))
        return tuple([x_pos, y_pos, z_pos])

    def get_df_with_fields(self):
        '''
        return a df with ephemeris states
        '''
        times = self.__getTimesList()
        latlong = self.__getLatLongList()
        sunlit_colors = self.__getSunlitColorList()   
        x_y_z = self.__getPosList() 
        return pd.DataFrame({'epoch': times, 'lat': latlong[0], 'lon': latlong[1], 'colors': sunlit_colors, 'x': x_y_z[0], 'y': x_y_z[1], 'z': x_y_z[2]})


class Satellite(EarthSatellite):
    '''
    Object that contains info about a satellite object and transit events
    '''
    def __init__(self, st_object):
        self.satrec_object = st_object # see above for attrs
        self.ephemeris = None # SatelliteEphemeris object

    def __createEphemeris(self, t_start, t_end):
        res = False
        try:
            self.ephemeris = SatelliteEphemeris(t_start, t_end, self.satrec_object)
            res = True
        except Exception as e:
            st.exception(f"Failed to create ephem, got error: {e}")
        return res

    def print_summary(self):
        '''
        Prints results summary for selected satellite.
        '''
        tle_epoch = self.satrec_object.epoch.utc_strftime(DT_FORMAT)
        sat_name = self.satrec_object.name
        st.info(f"Showing results for: {sat_name} | TLE Epoch: {tle_epoch} UTC")
        objClassification = {"U": "Unclassified", "S": "Secret", "C": "Classified"}

        tab1, tab2, tab3 = st.tabs(["Mean Elements", "Identifier Info", "Propagation Status"])
        with tab1:
            col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
            altitude = (self.satrec_object.model.am - 1) * self.satrec_object.model.radiusearthkm
            col1.metric("Altitude (km):", f'{altitude:.2f}')
            col2.metric("Inclination (deg):", f'{np.rad2deg(self.satrec_object.model.im):.1f}')
            col3.metric("Arg. Perigee (deg):", f'{np.rad2deg(self.satrec_object.model.om):.1f}')
            col4.metric("RAAN (deg):", f'{np.rad2deg(self.satrec_object.model.Om):.1f}')
            col5.metric("Eccentricity:", f'{self.satrec_object.model.em:.1e}')
        with tab2:
            col1, col2, col3, col4 = st.columns([1,1,2,1.5])
            col1.metric("NORAD ID:", self.satrec_object.model.satnum)
            col2.metric("Launch Date:", f"'{self.satrec_object.model.intldesg[0:2]}")
            col3.metric("Classicification:", objClassification[self.satrec_object.model.classification])
            col4.metric("International Designator:", self.satrec_object.model.intldesg)
        with tab3:
            col1, col2 = st.columns([1,5])
            ts = load.timescale()
            t_now = ts.now()
            days = t_now - self.satrec_object.epoch
            col1.metric("TLE Age (days):", f'{days:.1f}')
            col2.metric("Propagation error code:", f'{cc.ERROR_CODES[str(self.satrec_object.model.error)]:.25s}')
        return None

    def plot_ground_tracks(self, dateChoice):
        '''
        generates an ephemeris for the satellite and plots the groun track
        '''
        ts = load.timescale()
        start_time = ts.from_datetime(dateChoice[0].replace(tzinfo=utc))
        end_time = ts.from_datetime(dateChoice[1].replace(tzinfo=utc))

        self.print_summary()

        if self.__createEphemeris(start_time, end_time):
            df_to_plot = self.ephemeris.get_df_with_fields()
            if DEBUG:
                print(f"Plotting {len(df_to_plot.epoch)} state vectors between " 
                      f"{start_time.utc_strftime(DT_FORMAT)} and {end_time.utc_strftime(DT_FORMAT)}")
        else:
            st.exception("Failed to generate ephemeris, can't plot ground tracks!")
        
        viewState = pdk.ViewState(latitude=0, longitude=0, zoom=0.1, pitch=0)
        layer_1 = pdk.Layer('ScatterplotLayer', data=df_to_plot, get_position='[lon, lat]',
                           get_color='colors', get_radius=7e4, pickable=True, auto_highlight=True)
        r = pdk.Deck(map_style=None, initial_view_state=viewState, layers=[layer_1])
        st.pydeck_chart(r)
        
        st.caption(f"Plotting {len(df_to_plot.epoch)} state vectors between " 
                   f"{start_time.utc_strftime(DT_FORMAT)} and {end_time.utc_strftime(DT_FORMAT)} UTC.")
        
        return r
        

