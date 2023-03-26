import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import satellite_utils as st_utils
from datetime import (datetime as dt, timedelta)
import constellation_configs as cc
import location_utils as loc_utils
from pytz import timezone

# Meta Info
st.set_page_config(page_title="Satellite Tracker")
st.subheader('Satellite Tracker 🛰 🛰 🛰')
st.caption(''' Explore in-depth information about a satellite 
and visualize ground tracks over a selected time range.
''')
st.write('Satellite Summary')

# UI Elements
# ------------------------- Sidebar panel
# Get user input:
st.sidebar.write('Begin here 👇')

# 1. Select a group of satellites
satellite_group_type = st.sidebar.selectbox('Select a satellite group:', tuple(cc.TLE_GROUP_URL))
_URL = 'http://celestrak.com/NORAD/elements/'
url = f'{_URL}{cc.TLE_GROUP_URL[satellite_group_type]}.txt'
satellites = load.tle_file(url, reload=True)
st.sidebar.success(f"Loaded {len(satellites)} satellites.",icon="✅")

# 2. Select satellite of interest
by_name = {f"NORAD ID: {sat.model.satnum:<6} | {sat.name}": sat for sat in satellites}
options = st.sidebar.selectbox('Select a satellite:', tuple(by_name))
satObject = st_utils.Satellite(by_name[str(options)])

usrLoc = loc_utils.UserLocation()
locationChoice = st.sidebar.multiselect('Select a Location', usrLoc.locations_list, ['BOULDER', 'MUMBAI'])
usrLoc.initialize_location_services(locationChoice, multi=True)
usrLoc.update_timezone(input_needed=False) # sets usrLoc.selected_tz to UTC by default

# 3. Get Date Range
start_time = dt.utcnow().replace(tzinfo=timezone('UTC'))
dateOptStart = dt(start_time.year, start_time.month, start_time.day, start_time.hour, 0, 0, 0, timezone(usrLoc.selected_tz))
dateChoice = st.sidebar.slider(
    f"Select time range (UTC):",
    min_value = dateOptStart,
    max_value = dateOptStart + timedelta(hours=8),
    value=(dateOptStart, dateOptStart + timedelta(hours=3)),
    step = (timedelta(minutes=90)),
    format = "MM/DD HH:mm")
usrLoc.initialize_time_services(dateChoice)


with st.spinner("Computing satellite ground tracks..."):
    satObject.plot_ground_tracks(dateChoice)

satObject.generatePasses(usrLoc)


