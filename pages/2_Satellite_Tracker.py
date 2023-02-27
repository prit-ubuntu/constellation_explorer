import streamlit as st
from skyfield.api import load
import satellite_utils as st_utils
from datetime import (datetime as dt, timedelta)
import constellation_configs as cc


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
satellites = load.tle_file(url)
st.sidebar.success(f"Loaded {len(satellites)} satellites.",icon="✅")

# 2. Select satellite of interest
by_name = {f"NORAD ID: {sat.model.satnum:<6} | {sat.name}": sat for sat in satellites}
options = st.sidebar.selectbox('Select a satellite:', tuple(by_name))
satObject = st_utils.Satellite(by_name[str(options)])

# 3. Get Date Range
start_time = dt.utcnow()
dateOptStart = dt(start_time.year, start_time.month, start_time.day, start_time.hour, 0, 0, 0)
dateChoice = st.sidebar.slider(
    f"Select time range (UTC):",
    min_value = dateOptStart,
    max_value = dateOptStart + timedelta(hours=8),
    value=(dateOptStart, dateOptStart + timedelta(hours=3)),
    step = (timedelta(minutes=90)),
    format = "MM/DD HH:mm")

# 4. Display Results
with st.spinner("Computing satellite ground tracks..."):
    satObject.plot_ground_tracks(dateChoice)

