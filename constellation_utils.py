import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import pandas as pd
import numpy as np
import constellation_configs as cc
import pydeck as pdk
import plotly.express as px

# Names of all constellations in config file
CONSTELLATIONS = list(cc.CONFIGS.keys())
_URL = 'http://celestrak.com/NORAD/elements/'

DEBUG_CACHE = False
DEBUG = False
DEBUG_DATA = False
VERBOSE = False

NUM_TRACK = 50
KM_BIN_SIZE = 100
INC_BIN_SIZE = 5
MAX_POINTS = 3000


class TransitEvent():
    '''
    Object that contains info about a transit event
    '''
    def __init__(self, rise_time, culminate_time, set_time, sat_name, satrecObj, goeposition, loc_name):
        self.rise = rise_time # ts objects
        self.culminate = culminate_time # ts objects
        self.set = set_time # ts objects
        self.asset = sat_name
        self.loc = goeposition # wgs84 GEOID object
        self.loc_name = loc_name # string from UserLocation.selected_loc
        self.geo_position = None # array of geocentric [x,y,z] (km) from rise to set 
        self.latlon = None # array of [lat,lon] (deg)
        self.azaltrange = None # array of [azimuth (deg), elevation (deg), range (km)] 

        if isinstance(satrecObj, EarthSatellite):
            self.satrec = satrecObj
        else:
            raise TypeError
            if DEBUG:
                print('Did not add satrec object!')
                

    def get_ephem(self):
        
        res = False

        ts = load.timescale()
        ts_range = ts.linspace(self.rise, self.set, NUM_TRACK)
        difference = self.satrec - self.loc

        geo_pos = np.zeros([NUM_TRACK, 3])
        lat_lon = np.zeros([NUM_TRACK, 2])
        azaltrange = np.zeros([NUM_TRACK, 3])

        for id, time in enumerate(ts_range):
            geocentric = self.satrec.at(time)
            lat, lon = wgs84.latlon_of(geocentric)

            topocentric = difference.at(time)
            alt, az, range = topocentric.altaz()

            azaltrange[id] = np.array([az.degrees, alt.degrees, range.km])
            geo_pos[id] = np.array([geocentric.position.km[0], geocentric.position.km[1], geocentric.position.km[2]])
            lat_lon[id] = np.array([lat.degrees, lon.degrees])
        
        self.geo_position = geo_pos
        self.latlon = lat_lon
        self.azaltrange = azaltrange
        res = True
        return res

    def is_populated(self):
        status = False
        check_latlon = self.latlon.shape == (2, NUM_TRACK)
        check_azaltrange = self.azaltrange.shape == (2, NUM_TRACK)
        check_position = self.geo_position.shape == (3, NUM_TRACK)

        if check_latlon and check_azaltrange and check_position:
            status = True
        else:
            if DEBUG: 
                print(f"Ephemeris not populated for event: {self}")
        return status

    def to_dict(self, tz):
        # utility for converting object into reportable data in given tz
        
        print(self.rise.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'))
        print(self.culminate.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'))
        print(self.set.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'))

        dict_ret = {
            'LOCATION': self.loc_name,
            'RISE': self.rise.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'CULMINATE': self.culminate.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'SET': self.set.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'ASSET': self.asset,
            'RISE_AZIMUTH': self.azaltrange[0][0],
            'SET_AZIMUTH': self.azaltrange[-1][0],
            'LAUNCH_YEAR': f"'{self.satrec.model.intldesg[0:2]}"
        }
 
        return dict_ret

    def __str__(self):
        return f"\n  Rise: {self.rise.utc_iso()} | Culminate: {self.culminate.utc_iso()} | Set: {self.set.utc_iso()}"

class SatelliteMember(EarthSatellite):
    '''
    Object that contains info about a satellite object and transit events
    '''
    def __init__(self, st_object):
        self.satrec_object = st_object # see above for attrs
        self.events = []

    def add_events(self, times, events, geoposition, for_loc):
        rise_events, culmination_events, setting_events = times[np.where(events==0)], times[np.where(events==1)], times[np.where(events==2)]
        # only add event if entire event is complete
        if len(rise_events) == len(culmination_events) == len(setting_events):
            for i in range(len(rise_events)):
                event = TransitEvent(rise_events[i], culmination_events[i], setting_events[i], self.satrec_object.name, self.satrec_object, geoposition, for_loc)
                # add event to list of events
                self.events.append(event)
        return None

    def create_ephemeris(self):
        res = False
        for event in self.events: 
            # populates lat/lon with time for event 
            res = event.get_ephem()
            if DEBUG and VERBOSE: 
                print(f"Using {NUM_TRACK} point per transit to compute ephems.")
        return res

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

        if constellation in CONSTELLATIONS:
            self.constellation = constellation
            self.min_elevation = cc.CONFIGS[constellation]['_MINELEVATIONS']
            self.max_altitude = cc.CONFIGS[constellation]['_MAXALTITUDES']
            self.radius_size = cc.CONFIGS[constellation]['_RADIUSLEVELS']
            self.map_zoom = cc.CONFIGS[constellation]['_ZOOMLEVELS']
        else:
            st.error('Need a constellation to begin!')

        self.initialized = False
        self.num_passes = 0
        self.unique_passes = 0
        # download satellite data
        self.satellites = self.get_sats()
        # To be filled by generated sched
        self.schedule = pd.DataFrame()
        # pandas df to be plotted
        self.stats_df = pd.DataFrame()

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
            if DEBUG_CACHE:
                print('CACHE CHECK: Queried new data!')
            url = f'{_URL}{self.constellation.lower()}.txt'
            try:
                satellites = load.tle_file(url)
                return satellites # EarthSatellite
            except Exception as e:
                st.error('Failed to get constellation data!')
        
        member_satellites = []
        satellites = query_url()

        # only add satellite with valid propagation
        for sat in satellites:
            alt = (sat.model.am - 1) * sat.model.radiusearthkm
            # will need to include this sanity check for adding satellite objects
            if sat.model.error == 0 and alt > 0 and alt < 2*self.max_altitude:
                member_satellites.append(SatelliteMember(sat))
            else:
                if DEBUG: 
                    print(f'Did not add sat with error code: {cc.ERROR_CODES[str(sat.model.error)]}, dropping sat...')

        self.initialized = True
        return member_satellites

    def generatePasses(self, usrLocObject):
        '''!
        @brief  Generate the passes of a specific constellation over a specified location and time range.

        @param usrLocObject    TUPLE of latitude and longitude        

        @return passes      generate passes vector
        '''

        def findTransits(usrLocObject):
            for sat in self.satellites:
                times, events = sat.satrec_object.find_events(self.cityLatLon, self.time[0], self.time[1], self.min_elevation)
                if len(events) > 0:
                    sat.add_events(times, events, self.cityLatLon, usrLocObject.selected_loc)
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
        # Adds transit events to each satellite
        findTransits(usrLocObject)
        # Returns a pandas dataframe and populates transit events with ephemeris info
        return self.getSchedule()

    def getSchedule(self):
        '''
        @return passes      PANDAS df [Satellite Name, Time of Rise (string), Culminate (string), Set (string)]
        '''

        def update_pass_stats():
            num_passes = 0
            num_sats_with_passes = 0
            for sat in self.satellites:
                if sat.events:
                    num_sats_with_passes += 1
                    num_passes += len(sat.events)
            self.num_passes = num_passes
            self.unique_passes = num_sats_with_passes
            return None

        def compute_ephems():
            '''
            @return None, computes points per transit based on number of transits and max points, for performance
            '''
            if self.num_passes > 0:
                global NUM_TRACK
                NUM_TRACK = int(MAX_POINTS / self.num_passes)
                for sat in self.satellites:
                    sat.create_ephemeris()
            else:
                if DEBUG:
                    print('Did not generate schedule as there are no transits!')
            return None

        def get_pd_df():
            if self.num_passes > 0:
                df_list = []
                for sat in self.satellites:
                    df_list.append(sat.get_events_df(self.tz))
                passes_df = pd.concat(df_list)
                self.schedule = passes_df
            else:
                if DEBUG:
                    print('Returning default empty DF, as there are no transits!')
            return self.schedule.copy()

        # get number of transits and update class attributes for transit stats
        update_pass_stats()

        # generate ephemeris based on num transits and max points per transit
        compute_ephems()

        # return pandas dataframe
        df_to_display = get_pd_df()

        return df_to_display

    def dropEvents(self):
        '''
        @return None, updates the constellation object with NO events
        '''
        if DEBUG:
            print('Dropped all events for satellites since time range / location was changed!')
        for sat in self.satellites:
            sat.drop_events()
        return None

    def showStats(self, usrLoc):
        '''
        @return None, shows all the plots / data
        '''
        
        def display_results_summary():
            col1, col2, col3, col4 = st.columns([1,1,1.5,2.5])
            col1.metric("Transits", self.num_passes)
            col2.metric("Satellites", self.unique_passes)
            col3.metric("Constellation", self.constellation)
            col4.metric(f"{self.min_elevation}° Above Horizon Over", usrLoc.selected_loc)
   
        def display_info_tab():
            with st.expander("See explanation"):
                    az_info_str = '''The azimuth is measured clockwise around the horizon, just like the degrees shown on a compass, 
                                    from geographic north (0°) through east (90°), south (180°), and west (270°) before returning 
                                    to the north and rolling over from 359° back to 0°. '''
                    st.info(az_info_str, icon="ℹ️")

                    tz_info_str = f'''All times reported are in local timezone of {usrLoc.selected_tz}.'''
                    st.info(tz_info_str, icon="ℹ️")

                    gTrack_info_str = f'''Limiting plotting to 6000 points total. 
                                       These points are divided amongst number of transits equally. '''
                    st.info(gTrack_info_str, icon="ℹ️")

        def display_transits(types):
            
            for type in types:            
                if type == "TABLE":
                    # print tabular schedule
                    transit_schedule = self.getTransits(purpose="TO_PRINT")
                    # 'ASSET', 'RISE', 'SET', 'RISE_AZIMUTH', 'SET_AZIMUTH'
                    st.dataframe(transit_schedule, use_container_width=True)
                elif type == "TIMELINE":
                    # plot timeline view
                    sked_for_tl = self.getTransits(purpose="FOR_TIMELINE")
                    sked_for_tl['Location'] = f"{usrLoc.selected_loc}"
                    # fig = px.timeline(sked_for_tl, x_start="RISE", x_end="SET", y='LAUNCH_YEAR')
                    fig = px.timeline(sked_for_tl, x_start="RISE", x_end="SET", y = "Location", color='ASSET', 
                                    hover_data={'ASSET':True, "RISE": False, "SET": False, 
                                    'RISE_AZIMUTH':':.2f', 'SET_AZIMUTH':':.2f', 'DURATION (sec)':':.2f'})
                    fig.update_yaxes(autorange="reversed")
                    # BUGGY - NEED TO RESOLVE
                    # st.plotly_chart(fig, theme="streamlit")
                elif type == "GROUND_TRACKS":
                    # plot ground tracks of transits
                    st.caption(f"Showing {NUM_TRACK} points for each ground track from transits over {usrLoc.selected_loc}.")
                    gTrack = self.generateGroundTracks()
                    st.pydeck_chart(gTrack)
                else:
                    raise ValueError('cant find my purpose!!')
            return None

        display_results_summary()

        tab1, tab2 = st.tabs(["Transits", "Constellation Statistics"])

        with tab1:
            if self.num_passes > 0:
                ele_info_str = f'''Showing transits over  {self.min_elevation}° of elevation above 
                                the horizon ({usrLoc.selected_tz} time).'''
                st.caption(ele_info_str)
                # display elements in this order
                display_transits(types=["TIMELINE","GROUND_TRACKS","TABLE"])
                display_info_tab()
            else:
                st.caption('No transists found in the given timeframe.')

        with tab2:
            # gets a pandas df for stats to be plotted
            self.getDataPDtoPlot()
            launchDist = self.getLaunchDist()
            st.plotly_chart(launchDist, theme="streamlit")
            smaHist = self.getSMADist()
            st.plotly_chart(smaHist, theme="streamlit")
            incDist = self.getIncDist()
            st.plotly_chart(incDist, theme="streamlit")
            st.caption(f"Showing results for {len(self.satellites)} satellites in {self.constellation} constellation.")
        return None

    def getTransits(self, purpose):
        '''
        returns dataframe based on purpose of request
        '''
        df = self.schedule.copy()
        if purpose == "TO_PRINT":
            # Only select a subset of columns
            df = df[['ASSET', 'RISE', 'SET', 'RISE_AZIMUTH', 'SET_AZIMUTH']]
            df.set_index('ASSET', inplace=True)
            df.sort_values(by='RISE', ascending=True, inplace=True)
            # df.rename(columns={"RISE": "a", "SET": "c"}, inplace=True)
        elif purpose == "FOR_TIMELINE":
            df = df[['ASSET', 'RISE', 'SET', 'RISE_AZIMUTH', 'SET_AZIMUTH', 'LAUNCH_YEAR']]
            df["RISE"] = pd.to_datetime(df["RISE"])
            df["SET"] = pd.to_datetime(df["SET"])
            df['DURATION (sec)'] = (df.SET - df.RISE) / pd.Timedelta(seconds=1)
            # df.rename(columns={"RISE": "a", "SET": "c"}, inplace=True)
        else:
            raise ValueError('cant find my purpose!!')
        return df

    def generateGroundTracks(self):
        lat_list, lon_list, asset_list = [], [], []
        for sat in self.satellites:
            for event in sat.events:
                if event.is_populated:
                    for node in event.latlon:
                        lat_list.append(node[0])
                        lon_list.append(node[1])
                        asset_list.append(event.asset)
                else:
                    if DEBUG:
                        print(f"Could not add event for ground tracks: {event}")

        chart_data = pd.DataFrame({"lat": lat_list, "lon": lon_list, "asset": asset_list})

        # Simple implementation
        # st.map(chart_data)
        viewState = pdk.ViewState(latitude=self.cityLatLon.latitude.degrees, 
                                  longitude=self.cityLatLon.longitude.degrees,
                                  zoom=self.map_zoom, pitch=0)

        layer_1 = pdk.Layer('ScatterplotLayer', data=chart_data, get_position='[lon, lat]',
                           get_color=[150, 249, 123], get_radius=self.radius_size, pickable=True, auto_highlight=True)

        r = pdk.Deck(map_style=None, initial_view_state=viewState, layers=[layer_1])
        return r

    def getDataPDtoPlot(self):

        a_mean_list = []
        name_list = []
        launch_year = []
        inc_list = []
        norad_list = []

        for sat in self.satellites:
            try:
                alt = (sat.satrec_object.model.am - 1) * sat.satrec_object.model.radiusearthkm
                if alt > 0 and alt < 2*self.max_altitude:
                    a_mean_list.append(alt) # kms
                    name_list.append(sat.satrec_object.name)
                    launch_year.append(f"'{sat.satrec_object.model.intldesg[0:2]}")
                    inc = sat.satrec_object.model.inclo # radians
                    inc_list.append(inc)
                    norad_list.append(sat.satrec_object.model.satnum)
            except:
                print(f'Found a prop error: {sat.satrec_object.model.error}')
                print(f'Could not add data for {sat.satrec_object.name}')

        inc_list = np.rad2deg(inc_list)

        df_to_plot = pd.DataFrame({'meanSMA (km)': a_mean_list, 'incl (deg)': inc_list, 'NORAD ID': norad_list, 'Asset': name_list, 'Launch Year': launch_year})
        self.stats_df = df_to_plot

        if DEBUG_DATA:
            st.dataframe(df_to_plot)

        return None

    def getLaunchDist(self):
        # Histogram of satelites launched per year
        df_to_plot = self.stats_df
        fig = px.histogram(df_to_plot, x="Launch Year", marginal="rug", color="Launch Year", title="# of Satellites Launched",hover_data=df_to_plot.columns) 
        return fig

    def getSMADist(self):
        # "Mean Semi-major Axis (km)"
        df_to_plot = self.stats_df
        fig = px.histogram(df_to_plot, x="meanSMA (km)", color="Launch Year", marginal="rug", title="Altitude Distribution (km)",hover_data=df_to_plot.columns)        
        # fig.update_layout(xaxis_range=[0, max(a_mean_list)])
        return fig

    def getIncDist(self):
        df_to_plot = self.stats_df
        # num_bins = int((max(inc_list) - min(inc_list)) / INC_BIN_SIZE)
        # "Inclination (deg)"
        fig = px.histogram(df_to_plot, x="incl (deg)", color="Launch Year", marginal="rug", title="Inclination Distribution (degrees)", hover_data=df_to_plot.columns)
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
