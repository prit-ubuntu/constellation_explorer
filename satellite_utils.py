import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import pandas as pd
import numpy as np
import pydeck as pdk
from skyfield.api import utc
from skyfield.positionlib import Geocentric
from skyfield.timelib import Time as SkyfieldTime
import constellation_configs as cc
from constellation_utils import TransitEvent
from sgp4 import exporter
import requests
import html_to_json
import json
import re
from datetime import datetime as dt
import plotly.express as px
import matplotlib.pyplot as plt
import plotly.graph_objects as go



NUM_TRACK = 500
NUM_TRACK_ENDPOINTS = 7
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
        color_list[:NUM_TRACK_ENDPOINTS] = [green_for_start] * NUM_TRACK_ENDPOINTS
        color_list[-NUM_TRACK_ENDPOINTS:] = [red_for_end] * NUM_TRACK_ENDPOINTS
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
        self.events = [] # array of transit events, filled by generatePasses
        self.min_elevation = 20 # degree above horizon for transits

    def get_min_elevation(self):
        help_str = "The angle of a satellite measured upwards from the observer's horizon. Thus, an object on the horizon has an elevation of 0° and one directly overhead has an elevation of 90°."
        self.min_elevation = st.sidebar.slider("Restrict transits above horizon (degrees):", min_value=0, max_value=80, value=30, step=10, help=help_str)
        return None

    def compute_transits(self, usrLocObject):

        def add_events(self, times, events, locObj, locName):
            rise_events, culmination_events, setting_events = times[np.where(events==0)], times[np.where(events==1)], times[np.where(events==2)]
            # only add event if entire event is complete
            if len(rise_events) == len(culmination_events) == len(setting_events):
                for i in range(len(rise_events)):
                    event = TransitEvent(rise_events[i], culmination_events[i], setting_events[i], self.satrec_object.name, self.satrec_object, locObj, locName)
                    event.get_ephem() # populate positional data for transits
                    self.events.append(event) # add event to list of events
                    if DEBUG:
                        print(event)
                if DEBUG:
                    print(f"Found {len(rise_events)} transits for {locName} for {self.min_elevation} degrees above the horizon.")
                    print("-"*45)
            return None
        
        def findTransits():
            for idx, loc in enumerate(usrLocObject.selected_position_array):
                cityLatLon = wgs84.latlon(loc[0], loc[1])
                ts = load.timescale()
                time_range = (ts.from_datetime(usrLocObject.date_range[0]), ts.from_datetime(usrLocObject.date_range[1]))
                times, events = self.satrec_object.find_events(cityLatLon, time_range[0], time_range[1], self.min_elevation)
                if len(events) > 0:
                    add_events(self, times, events, cityLatLon, usrLocObject.selected_loc_array[idx])

            if DEBUG:
                if len(self.events) > 0:
                    print(f"Found {len(self.events)} events for {len(usrLocObject.selected_position_array)} locations.")
                else:
                    print(f"Found no transits for these locations: {usrLocObject.selected_loc_array}")

        findTransits()
    
        df_to_print = pd.DataFrame() # return empty df by default if no events found

        if self.events:
            list_of_recs = [ev.to_dict(usrLocObject.date_range[0].tzinfo) for ev in self.events]
            df_to_print = pd.DataFrame.from_records(list_of_recs)
            # df_to_print = df_to_print[['LOCATION', 'RISE', 'SET']] # RISE/SET_AZIMUTH not available since 
            df_to_print = df_to_print[['LOCATION', 'RISE', 'SET', 'RISE_AZIMUTH', 'SET_AZIMUTH']]
            df_to_print.set_index('LOCATION', inplace=True)
            df_to_print.sort_values(by='RISE', ascending=True, inplace=True)
        
        return df_to_print

    def __createEphemeris(self, t_start, t_end):
        res = False
        try:
            self.ephemeris = SatelliteEphemeris(t_start, t_end, self.satrec_object)
            res = True
        except Exception as e:
            st.exception(f"Failed to create ephem, got error: {e}")
        return res

    def drop_events(self):
        # used for callback when location / time range changes, we do not want to remember events
        self.events = []

    def print_summary(self):
        '''
        Prints results summary for selected satellite.
        '''
        tle_epoch = self.satrec_object.epoch.utc_strftime(DT_FORMAT)
        st.info(f"Showing results for: {self.satrec_object.name} | NORAD ID: {self.satrec_object.model.satnum} | TLE Epoch: {tle_epoch} UTC")
        objClassification = {"U": "Unclassified", "S": "Secret", "C": "Classified"}

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Mean Elements", "Identifier Info", "TLE", "Propagation Status", "Satellite Orbital Trends"])
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
            col3.metric("Classification:", objClassification[self.satrec_object.model.classification])
            col4.metric("International Designator:", self.satrec_object.model.intldesg)
        with tab3:
            ts = load.timescale()
            t_now = ts.now()
            days = t_now - self.satrec_object.epoch
            line0 = self.satrec_object.name
            line1, line2 = exporter.export_tle(self.satrec_object.model)
            tle_example = f"{line0}\n{line1}\n{line2}\n"
            help_str = '''Spacing between elements might need adjustment for TLE checksums to match.
                          See [TLE Wikipedia](https://en.wikipedia.org/wiki/Two-line_element_set) for more info.
            '''
            st.text_area(f"TLE Epoch: {tle_epoch} UTC | TLE Age (days): {days:.1f}", tle_example, disabled=True, help=help_str)
        with tab4:
            col1, col2 = st.columns([1,1])
            col1.metric("Propagation error code:", f'{cc.ERROR_CODES[str(self.satrec_object.model.error)]:.25s}')
        with tab5:
            try:
                fig = self.get_orbital_trends()
                st.plotly_chart(fig, theme="streamlit")
            except Exception as e:
                print(f'Encountered an error while querying celes trek: {e}, only showing link, no plot.')
                celes_request = f"http://celestrak.org/NORAD/elements/graph-altitude.php?CATNR={self.satrec_object.model.satnum}"
                st.write(f"See historical mean elements on [Celestrak]({celes_request}).")
        return None
    
    def get_orbital_trends(self, use_only_altitude = False):
        
        if use_only_altitude:
            # columns = ['Date', 'Apogee', 'Perigee', 'Eccentricity']
            celes_request = f"http://celestrak.org/NORAD/elements/graph-altitude.php?CATNR={self.satrec_object.model.satnum}"
        else:
            # columns = ['Date', 'RAAN', 'Inclination', 'Arg of Perigee', 'SMA', 'Eccentricity']
            celes_request = f"http://celestrak.org/NORAD/elements/graph-orbit-data.php?CATNR={self.satrec_object.model.satnum}"

        resp = requests.get(celes_request)
        output_json = html_to_json.convert(resp.text)

        if DEBUG:
            with open(f'{self.satrec_object.model.satnum}_plotphp_req.json', 'w') as f:
                f.write(json.dumps(output_json, indent=1))

        plot_str = output_json["html"][0]["body"][0]["script"][0]["_value"]
        only_comm = plot_str.split('var plotData = \"')[1].split('|\";')[0]
        splt_comm = re.split(r'\|', only_comm)
        table = [re.split(r',', row_item) for row_item in splt_comm]
        columns = table[0]
        json_obj = {}
        dt_vec = []
        
        for idx, col in enumerate(columns):
            if col == "Date":
                format_str = "%Y-%m-%dT%H:%M:%S.%f"
                dt_vec = [dt.strptime(datapoint[idx],format_str) for datapoint in table[1:]]
                json_obj[col] = [datapoint[idx] for datapoint in table[1:]]
            else:
                json_obj[col] = [float(datapoint[idx]) for datapoint in table[1:]]
        
        df_hist = pd.DataFrame(json_obj)

        if DEBUG:
            with open(f'{self.satrec_object.model.satnum}_plotphp_js.json', 'w') as f:
                f.write(json.dumps(json_obj, indent=1))
            st.dataframe(df_hist, use_container_width=True)
        
        fig1 = go.Figure()
        fig1.update_xaxes(rangeslider_visible=True, rangeselector=dict(buttons=list([
                            dict(count=1, label='1m', step='month', stepmode='backward'),
                            dict(count=6, label='6m', step='month', stepmode='backward'),
                            dict(count=1, label='YTD', step='year', stepmode='todate'),
                            dict(count=1, label='1y', step='year', stepmode='backward'),
                            dict(step='all')])))

        if use_only_altitude:
            # columns = ['Date', 'Apogee', 'Perigee', 'Eccentricity']
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['Apogee'], name='Apogee (km)', mode='lines'))
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['Perigee'], name='Perigee (km)', mode='lines'))
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['Eccentricity'], name='Eccentricity', yaxis="y3", hovertemplate = '%{y:.4e}'))
            fig1.update_layout(
                xaxis  = {'title': 'Date'},
                yaxis  = {'title': 'Altitude (km)', 'autoshift': True},
                yaxis3 = {'title': 'Eccentricity', 'overlaying': 'y', 'side': 'right', 'autoshift': True},
                hovermode = "x unified",
                legend = {'orientation' : 'h', 'xanchor':'right', 'x': 1, 'yanchor': 'bottom', 'y': 1}, 
                title_text=f"{self.satrec_object.name} | NORAD ID: {self.satrec_object.model.satnum}")
        else:
            # columns = ['Date', 'RAAN', 'Inclination', 'Arg of Perigee', 'SMA', 'Eccentricity']
            # https://plotly.com/python/multiple-axes/#shift-axes-by-a-specific-number-of-pixels 
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['RAAN'], name='RAAN (deg)', mode='lines'))
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['Inclination'], name='Inclination (deg)', mode='lines', yaxis="y2"))
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['Eccentricity'], name='Eccentricity', hovertemplate = '%{y:.4e}', yaxis="y3"))
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['SMA'], name='Sem-major Axis Altitude (km)', mode='lines', yaxis="y4"))
            fig1.add_trace(go.Scatter(x = df_hist['Date'], y = df_hist['Arg of Perigee'], name='Argument of Perigee (deg)', mode='lines', yaxis="y5"))
            fig1.update_layout( 
                # xaxis = {'title': 'Date', 'domain': [0.25, 0.9], 'tickformat' : '%Y-%m-%dT%H:%M:%SZ'},
                xaxis = {'title': 'Date', 'domain': [0.25, 0.8]},
                yaxis  = {'title': {'text': 'RAAN (deg)', 'standoff': 1}, 'side': 'left', 'autoshift': True},
                yaxis2 = {'title': {'text': 'Inclination (deg)', 'standoff': 1}, 'overlaying': 'y', 'anchor': 'free', 'autoshift': True, 'position': 0.13},
                yaxis3 = {'title': {'text': 'Eccentricity', 'standoff': 15} , 'overlaying': 'y', 'side': 'right', 'position': 0.99, 'autoshift': True},
                yaxis4 = {'title': {'text': 'SMA (km)', 'standoff': 0}, 'overlaying': 'y',  'side': 'right', 'autoshift': True, 'autorange': True},
                yaxis5 = {'title': {'text': 'Argument of Perigee (deg)', 'standoff': 18} , 'overlaying': 'y', 'position': 0.01, 'anchor': 'free', 'autoshift': True},
                hovermode = 'x unified',
                legend = {'orientation' : 'h', 'xanchor': 'right', 'x': 1, 'yanchor': 'bottom', 'y': -1},
                title_text=f"{self.satrec_object.name} | NORAD ID: {self.satrec_object.model.satnum}")
        
        st.caption(f"Showing {len(table)} historical mean elements from [Celestrak]({celes_request}).")
        return fig1

    def get_location_df(self, usrLoc):

        lat = [lat_lon_position_pair[0] for lat_lon_position_pair in usrLoc.selected_position_array]
        lon = [lat_lon_position_pair[1] for lat_lon_position_pair in usrLoc.selected_position_array]
        white = [255, 255, 255] 
        yellow = [255, 140, 0]
        loc_for_events = [event.loc_name for event in self.events]
        valid_transit_list = [loc in loc_for_events for loc in usrLoc.selected_loc_array]
        location_colors = [yellow if is_valid_transit else white for is_valid_transit in valid_transit_list]
        df = pd.DataFrame(data = {"epoch": usrLoc.selected_loc_array, "lat": lat, "lon": lon, "colors": location_colors}) # dummy epoch column to spoof labelling in pdk.Deck call below
        return df

    def display_results(self, dateChoice, usrLoc):
        '''
        generates an ephemeris for the satellite and plots the groun track
        '''
        
        if dateChoice[1] == dateChoice[0]:
            st.error('Please select a different stop time, start time and stop time cannot be same!')
        else:
            
            with st.spinner("Computing satellite ground tracks..."):
                ts = load.timescale()
                start_time = ts.from_datetime(dateChoice[0].replace(tzinfo=utc))
                end_time = ts.from_datetime(dateChoice[1].replace(tzinfo=utc))

                self.print_summary()

                if self.__createEphemeris(start_time, end_time):
                    df_to_plot = self.ephemeris.get_df_with_fields()
                    if DEBUG:
                        print(f"Plotting {len(df_to_plot.epoch)} ground tracks between " 
                            f"{start_time.utc_strftime(DT_FORMAT)} and {end_time.utc_strftime(DT_FORMAT)}")
                else:
                    st.exception("Failed to generate ephemeris, can't plot ground tracks!")
                
            # compute transits, print later (see bottom), critical for transit events to be populated
            with st.spinner("Computing transit schedule..."):
                df_transit_schedule_to_print = self.compute_transits(usrLoc)
                df_for_plot_loc = self.get_location_df(usrLoc)
            
            # show ground tracks and locations
            with st.spinner("Ploting ground tracks..."):
                viewState = pdk.ViewState(latitude=0, longitude=0, zoom=0.1, pitch=0)
                layer_groundtracks = pdk.Layer('ScatterplotLayer', data=df_to_plot, get_position='[lon, lat]',
                                get_color='colors', get_radius=7e4, pickable=True, auto_highlight=True, 
                                radius_min_pixels=1, radius_max_pixels=100)
                layer_locations = pdk.Layer( "ScatterplotLayer", df_for_plot_loc, 
                                pickable=True, opacity=1, stroked=True, 
                                filled=True, radius_scale=6, 
                                radius_min_pixels=1, radius_max_pixels=100, line_width_min_pixels=1, 
                                get_position="[lon, lat]", get_radius=3.5e4, 
                                get_fill_color="colors", get_line_color=[0, 0, 0])
                
                r = pdk.Deck(map_style=None, initial_view_state=viewState, layers=[layer_groundtracks, layer_locations], tooltip={"text":"{epoch}"})
                st.pydeck_chart(r)

                with st.expander("See point coloring legend:"):
                    legen_str = ''' 1. Illumination Status: Yellow = Sunlit | Purple = Eclipsed
                                \n 2. Orbit Direction: Green = Orbit Start | Red = Orbit End
                                \n 3. Location Status: White = Without transit | Orange = With transits
                                '''
                    st.caption(legen_str)

                st.sidebar.caption(f'''
                            Plotting {len(df_to_plot.epoch)} ground tracks between
                            {start_time.utc_strftime(DT_FORMAT)} and {end_time.utc_strftime(DT_FORMAT)} UTC.
                            ''')

            if not df_transit_schedule_to_print.empty:
                st.dataframe(df_transit_schedule_to_print, use_container_width=True)
            else:
                st.warning('No transists found in the given timeframe.')
                
        return None
        

