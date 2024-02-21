import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import pandas as pd
import numpy as np
import constellation_configs as cc
import pydeck as pdk
import plotly.express as px
import random
import requests

# Names of all constellations in config file
CONSTELLATIONS = list(cc.CONFIGS.keys())
DT_FORMAT = '%b %d, %Y %H:%M:%S'

DEBUG_CACHE = False
DEBUG = False
DEBUG_DATA = False
VERBOSE = False
MULTI_COLOR = True

NUM_TRACK = 50
KM_BIN_SIZE = 100
INC_BIN_SIZE = 5
MAX_POINTS = 3000
STALE_EPOCH = 5 # days

ts = load.timescale()

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
        self.time_list = None # list of times for display

        if isinstance(satrecObj, EarthSatellite):
            self.satrec = satrecObj
        else:
            raise TypeError
            if DEBUG:
                print('Did not add satrec object!')
                

    def get_ephem(self):
        
        res = False

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
        self.time_list = ts_range
        res = True
        return res

    def is_populated(self):
        status = False
        check_latlon = self.latlon.shape == (NUM_TRACK, 2)
        check_azaltrange = self.azaltrange.shape == (NUM_TRACK, 3)
        check_position = self.geo_position.shape == (NUM_TRACK, 3)
        check_time_nodes = len(self.time_list) == NUM_TRACK

        if check_time_nodes and check_latlon and check_azaltrange and check_position:
            status = True
        else:
            if DEBUG:
                print(f"Ephemeris not populated for event: {self}")
        return status

    def get_printable_times(self, format=DT_FORMAT):
        '''
        returns a list of time strings for all state vector epochs
        '''
        return [time.utc_strftime(format) for time in self.time_list]

    def to_dict(self, tz):
        # utility for converting object into reportable data in given tz
        rise_az, set_az = 0, 0 # use defaults for safety and bring up any errors
        if self.is_populated():
            rise_az, set_az = self.azaltrange[0][0], self.azaltrange[-1][0]

        dict_ret = {
            'LOCATION': self.loc_name,
            'RISE': self.rise.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'CULMINATE': self.culminate.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'SET': self.set.utc_datetime().astimezone(tz).strftime('%b %d, %Y %H:%M:%S'),
            'ASSET': self.asset,
            'RISE_AZIMUTH': rise_az,
            'SET_AZIMUTH': set_az,
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

@st.cache_resource(ttl=21600)
def get_data_from_spacetrack(const_name, query_limit=10000):
    
    uriBase                = "https://www.space-track.org"
    requestLogin           = "/ajaxauth/login"
    requestCmdAction       = "/basicspacedata/query" 
    requestURL = cc.CONFIGS[const_name]["_URL"] + f"/limit/{query_limit}"

    with requests.Session() as session:
        # need to log in first. note that we get a 200 to say the web site got the data, not that we are logged in
        siteCred = {'identity': st.secrets.configuration.username, 'password': st.secrets.configuration.password}
        resp = session.post(uriBase + requestLogin, data = siteCred)
        if resp.status_code != 200:
            st.error("Could not reach Spacetrack!")
        # make get request from Spacetrack using the URL + auth
        resp = session.get(uriBase + requestCmdAction + requestURL)  
        if resp.status_code != 200:
            st.error("API query failed from Spacetrack!")
        else:
            session.close()
            # Convert text to bytearray
            lines = resp.text.splitlines()
            satellites = []
            for index in range(0, len(lines), 3):
                line_0, line_1, line_2 = lines[index:index+3]
                satellite = EarthSatellite(line_1, line_2, line_0[1:], ts)
                # print(satellite)
                satellites.append(satellite)
            return satellites

class SatConstellation(object):
    '''
    Object that contains all relevant information and methods for constellation!
    '''
    def __init__(self, constellation):
        if constellation in CONSTELLATIONS:
            self.constellation = constellation
            self.min_elevation = cc.CONFIGS[constellation]['_MINELEVATIONS']
            self.radius_size = cc.CONFIGS[constellation]['_RADIUSLEVELS']
            self.map_zoom = cc.CONFIGS[constellation]['_ZOOMLEVELS']
        else:
            st.error('Need a constellation to begin!')

        help_str = "The angle of a satellite measured upwards from the observer's horizon. Thus, an object on the horizon has an elevation of 0° and one directly overhead has an elevation of 90°."
        self.min_elevation = st.sidebar.slider("Restrict transits above horizon (degrees):", min_value=0, max_value=80, value=70, step=10, help=help_str)
        self.radius_size = st.sidebar.slider("Point radius size:", min_value=500, max_value=6000, value=1000, step=300)
        
        global MAX_POINTS
        MAX_POINTS = st.sidebar.slider("Max number of points on plot:", min_value=1000, max_value=10000, value=6000, step=1000)

        self.initialized = False
        self.num_passes = 0
        self.unique_passes = 0
        # download satellite data
        self.notif_msgs = ""
        self.query_sat_count = 0
        self.drop_count = 0
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

        def load_file():
            uploaded_file = st.file_uploader("Choose a valid TLE file (*.txt)", type = "txt")
            sats = []
            if uploaded_file is not None:
                sats = load.tle_file(uploaded_file.name)
            if len(sats) > 0:
                return sats
            else:
                raise Exception("BAD_FILE_READ_ERROR")
        member_satellites = []
        # only add satellite with valid propagation
        try:
            if self.constellation != "CUSTOM":
                satellites = get_data_from_spacetrack(self.constellation)
                self.initialized = True 
            else:
                satellites = load_file()
            # Saved queried number of satellites.
            self.query_sat_count = len(satellites)
            # Report successful query completion
            self.notif_msgs = f"Processing {len(satellites)} satellites from Spacetrack.\n"
            self.notif_msgs = self.notif_msgs + "-"*45
            # filter satellites for deorbitted sats just in case
            log_msg = None
            for sat in satellites:
                alt = (sat.model.am - 1) * sat.model.radiusearthkm
                tle_age = abs(ts.now() - sat.epoch)
                if tle_age > STALE_EPOCH:
                    log_msg = f"❌ Dropping sat: {sat}\n Reason: stale TLE, tle age: {tle_age:.2f} days"
                    self.drop_count += 1
                elif sat.model.error != 0:
                    log_msg = f"❌ Dropping sat: {sat}\n Reason: propagation error, code: {cc.ERROR_CODES[str(sat.model.error)]}"
                    self.drop_count += 1
                elif alt < 150:
                    log_msg = f"❌ Dropping sat: {sat}\n Reason: unrealistic altitude: {alt:.2f} km"
                    self.drop_count += 1           
                else:
                    log_msg = f"✅ Adding sat: {sat}\n Passed: QA checks - tle age: {tle_age:.2f} days, altitude: {alt:.0f} km"
                    member_satellites.append(SatelliteMember(sat))
                self.notif_msgs = f"{self.notif_msgs}\n" + log_msg + f"\n" + "-"*25 
            self.notif_msgs = f"{self.notif_msgs}" + "-"*25 + f"\n🛠️ Processed {len(satellites)} sats\n" + f"❌ Dropped {self.drop_count} sats\n" + f"✅ Saved {len(satellites) - self.drop_count} sats\n" 

        except Exception as e:
            st.error(f"Something went horribly wrong, sorry. {e}")
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

                    gTrack_info_str = f'''Limiting plotting to {MAX_POINTS} points total. 
                                       These points are divided amongst number of transits equally. '''
                    st.info(gTrack_info_str, icon="ℹ️")

        def display_transits(types):
            for type in types:        
                if type == "TABLE":
                    ele_info_str = f'''Showing transits over  {self.min_elevation}° of elevation above 
                                the {usrLoc.selected_loc} horizon (all times in {usrLoc.selected_tz} timezone).'''
                    st.caption(ele_info_str)
                    # print tabular schedule
                    transit_schedule = self.getTransits(purpose="TO_PRINT")
                    # 'ASSET', 'RISE', 'SET', 'RISE_AZIMUTH', 'SET_AZIMUTH'
                    st.dataframe(transit_schedule, use_container_width=True)
                elif type == "TIMELINE":
                    try:
                        # plot timeline view
                        sked_for_tl = self.getTransits(purpose="FOR_TIMELINE")
                        sked_for_tl['Location'] = f"{usrLoc.selected_loc}"
                        # fig = px.timeline(sked_for_tl, x_start="RISE", x_end="SET", y='LAUNCH_YEAR')
                        fig = px.timeline(sked_for_tl, x_start="RISE", x_end="SET", y = "Location", color='ASSET', 
                                        hover_data={'ASSET':True, "RISE": False, "SET": False, 
                                        'RISE_AZIMUTH':':.2f', 'SET_AZIMUTH':':.2f', 'DURATION (sec)':':.2f'})
                        fig.update_yaxes(autorange="reversed")
                        # BUGGY - NEED TO RESOLVEd
                        st.plotly_chart(fig, theme="streamlit")
                    except Exception as e:
                        print("Encountered an exception while displaying timeline: ", e)
                        st.warning("Sorry, something went wrong, could not display timeline.")
                elif type == "GROUND_TRACKS":
                    # plot ground tracks of transits
                    try:
                        st.caption(f"Showing {NUM_TRACK} points for each ground track from transits for {self.constellation} satellite constellation over {usrLoc.selected_loc}.")
                        gTrack = self.generateGroundTracks()
                        st.pydeck_chart(gTrack)
                    except Exception as e:
                        print("Encountered an exception while displaying ground tracks: ", e)
                        st.warning("Sorry, something went wrong.")
                else:
                    raise ValueError('cant find my purpose!!')
            return None

        display_results_summary()

        tab1, tab2, tab3 = st.tabs(["Transits", "Constellation Statistics", "Logs"])

        with tab1:
            if self.num_passes > 0:
                # display elements in this order
                display_transits(types=["GROUND_TRACKS","TABLE","TIMELINE"])
                display_info_tab()
            else:
                st.caption('No transists found in the given timeframe.')

        with tab2:
            # gets a pandas df for stats to be plotted
            st.caption(f"Showing results for {len(self.satellites)} satellites in {self.constellation} constellation that are still in orbit.")
            self.getDataPDtoPlot()
            launchDist = self.getLaunchDist()
            st.plotly_chart(launchDist, theme="streamlit")
            smaHist = self.getSMADist()
            st.plotly_chart(smaHist, theme="streamlit")
            incDist = self.getIncDist()
            st.plotly_chart(incDist, theme="streamlit")
        
        with tab3:
            summary_txt = f"🛠️ Processed {self.query_sat_count} sats\n" + f"❌ Dropped {self.drop_count} sats\n" + f"✅ Saved {self.query_sat_count - self.drop_count} sats" 
            st.text_area("QA Summary", summary_txt, disabled=True)
            st.text_area("Extended Logs", self.notif_msgs, disabled=True)

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
        lat_list, lon_list, asset_list, label_list, color_list = [], [], [], [], []
        for sat in self.satellites:
            rand_r, rand_g, rand_b = random.randint(0,255), random.randint(0,255), random.randint(0,255)
            for event in sat.events:
                if event.is_populated():
                    time_nodes = event.get_printable_times()
                    for idx, node in enumerate(event.latlon):
                        lat_list.append(node[0])
                        lon_list.append(node[1])
                        azimuth = round(event.azaltrange[idx][0],2)
                        elevation = round(event.azaltrange[idx][1],2)
                        asset_list.append(event.asset)
                        label_dp = f'''{event.asset} ({sat.satrec_object.model.satnum}) 
                                        Epoch: {time_nodes[idx]}
                                        Alt/Azm: {elevation}/{azimuth}
                                        Lat/Lon: {round(node[0],2)}/{round(node[1],2)}'''
                        label_list.append(label_dp)
                        if "FM-" in event.asset:
                            color_list.append([0, 255, 0])
                        else:
                            if MULTI_COLOR:
                                color_list.append([rand_r, rand_g, rand_b]) # plot different colors
                            else:
                                color_list.append([255, 255, 255])
                else:
                    print(f"did not add this event: {event}")
                    if DEBUG:
                        print(f"Could not add event for ground tracks: {event}")
                
        chart_data = pd.DataFrame({"epoch": label_list, "lat": lat_list, "lon": lon_list, "asset": asset_list, "colors": color_list})

        # Simple implementation
        # st.map(chart_data)
        viewState = pdk.ViewState(latitude=self.cityLatLon.latitude.degrees, 
                                  longitude=self.cityLatLon.longitude.degrees,
                                  zoom=self.map_zoom, pitch=0)

        layer_1 = pdk.Layer('ScatterplotLayer', data=chart_data, get_position='[lon, lat]',
                           get_color='colors', get_radius=self.radius_size, 
                           pickable=True, auto_highlight=True,
                           opacity=0.4, stroked=True,
                           radius_min_pixels=1, radius_max_pixels=100)

        r = pdk.Deck(map_style=None, initial_view_state=viewState, layers=[layer_1], tooltip={"text":"{epoch}"})
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
        fig = px.histogram(df_to_plot, x="Launch Year", marginal="rug", color="Launch Year", title=f"{self.constellation} - No. of Satellites Launched",hover_data=df_to_plot.columns) 
        return fig

    def getSMADist(self):
        # "Mean Semi-major Axis (km)"
        df_to_plot = self.stats_df
        fig = px.histogram(df_to_plot, x="meanSMA (km)", color="Launch Year", marginal="rug", title=f"{self.constellation} - Altitude Distribution (km)",hover_data=df_to_plot.columns)        
        # fig.update_layout(xaxis_range=[0, max(a_mean_list)])
        return fig

    def getIncDist(self):
        df_to_plot = self.stats_df
        # num_bins = int((max(inc_list) - min(inc_list)) / INC_BIN_SIZE)
        # "Inclination (deg)"
        fig = px.histogram(df_to_plot, x="incl (deg)", color="Launch Year", marginal="rug", title=f"{self.constellation} - Inclination Distribution (degrees)", hover_data=df_to_plot.columns)
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
