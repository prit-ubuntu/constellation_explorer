import streamlit as st
import constellation_utils as const_utils
import location_utils as loc_utils
import pandas as pd
from datetime import (datetime as dt, timedelta)
from pytz import timezone

# Meta Info
st.set_page_config(page_title='Constellation Transit Finder', page_icon="🔭", initial_sidebar_state='expanded')
st.title('Constellation Explorer 🛰 🛰 🛰')
st.write('Explore transits of satellites from the biggest constellations for over any area on Earth.')
st.subheader('Satellite Transit Summary')

# After main page title
def get_results(constObj):
    # After constellation data is retrieved, compute transits
    if constObj.initialized and usrLoc.initialized:
        constObj.generatePasses(usrLoc)
        constObj.showStats(usrLoc)
    else:
        st.error('Will need to fix issues before we can proceed.')

def update_events(const_to_change):
    # Used a callback to drop events for stale loc, timerange
    const_to_change.dropEvents()

# UI Elements
# ------------------------- Sidebar panel
# Get user input:
st.sidebar.title('Begin here 👇')

# 1. Get Constellation
constellationChoice = st.sidebar.selectbox('Select a Constellation', const_utils.CONSTELLATIONS)
@st.experimental_singleton(ttl=1200) # this will cache satellite data so we do not keep making requests to Celestrak
def getCachedConstellation(constellationName):
    constellation = const_utils.SatConstellation(constellationName)
    return constellation
constellation = getCachedConstellation(constellationChoice)
if constellation.initialized:
    st.sidebar.success(f"Queried {len(constellation.satellites)} {constellation.constellation} satellites.", icon="✅")

# 2. Get Location 
usrLoc = loc_utils.UserLocation()
locationChoice = st.sidebar.selectbox('Select a Location', usrLoc.locations_list, on_change=update_events, args=(constellation,))
usrLoc.initialize_location_services(locationChoice)
lat_long_input_disabled = True
if locationChoice == "CUSTOM LOCATION":
    lat_long_input_disabled = False
st.sidebar.columns(2)
lat = st.sidebar.number_input('Latitude', min_value= -90.0, max_value= 90.0, value=usrLoc.locations_dict[usrLoc.selected_loc][0], disabled=lat_long_input_disabled, on_change=update_events, args=(constellation,))
lon = st.sidebar.number_input('Longitude', min_value= -180.0, max_value=180.0, value=usrLoc.locations_dict[usrLoc.selected_loc][1], disabled=lat_long_input_disabled, on_change=update_events, args=(constellation,))
usrLoc.selected_position = (lat, lon)
usrLoc._update_timezone()

if usrLoc.initialized:
    st.sidebar.success(f"Timezone Identified: {usrLoc.selected_tz}.", icon="✅")

# 3. Get Date Range
currentDate = dt.now(timezone(usrLoc.selected_tz))
dateOptStart = dt(currentDate.year, currentDate.month, currentDate.day, currentDate.hour, 0, 0, 0, timezone(usrLoc.selected_tz))
dateChoice = st.slider(
    f"Select time range (_timezone: {usrLoc.selected_tz})_:",
    min_value = dateOptStart,
    max_value = dateOptStart + timedelta(days=3),
    value=(dateOptStart, dateOptStart + timedelta(days=1, hours=12)),
    step = (timedelta(hours=6)),
    format = "MM/DD/YY - HH:mm", on_change=update_events, args=(constellation,))
usrLoc.initialize_time_services(dateChoice)
if usrLoc.timerangeset:
    with st.spinner("Computing transit schedule..."):
        get_results(constellation) # display on main page
else:
    st.error('Please select a different time range!')

# 4. Display Map
st.sidebar.map(data=pd.DataFrame({'lat': usrLoc.selected_position[0], 'lon': usrLoc.selected_position[1]}, index=[0]), zoom=5, use_container_width=True)

# 5. About Section
st.sidebar.header('**About**')
st.sidebar.write('''
This app uses satellite positional data captured inside TLEs (Two Line Element Sets) from [Celestrak](http://celestrak.org/NORAD/elements/) that are propagated by [Skyfield API](https://rhodesmill.org/skyfield/) which leverages 
the sgp4 library. Get started by selecting a constellation in the sidebar, happy exploring!
''')
st.sidebar.write('''
This tool was co-created by [Prit Chovatiya](https://www.linkedin.com/in/prit-chovatiya/) and [Michael Levy](https://www.linkedin.com/in/levymp/) from their shared love of streamlit and passion for satellite constellations. 
''')