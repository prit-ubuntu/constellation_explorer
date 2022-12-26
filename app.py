import streamlit as st
import constellation_utils as const_utils
from location_utils import UserLocation
import pandas as pd

# Sidebar panel
st.set_page_config(page_title='Constellation Transit Finder', page_icon="🔭", initial_sidebar_state='expanded')

# App Summary 
st.title('Constellation Explorer 🛰 🛰 🛰')
st.write('''
Explore transits of satellites from the biggest constellations for over any area on Earth. 
This app uses satellite positional data captured inside TLEs (Two Line Element Sets) from [Celestrak](http://celestrak.org/NORAD/elements/) that are propagated by [Skyfield API](https://rhodesmill.org/skyfield/) which leverages 
the sgp4 library. Get started by selecting a constellation in the sidebar, happy exploring!
''')

# Get user input:
st.sidebar.title('Begin here 👇')

#   1. Constellation
st.sidebar.write('**Select a Constellation**')
constellationChoice = st.sidebar.selectbox('_placeholder_', const_utils.CONSTELLATIONS, label_visibility='collapsed')

#   2. Location 
st.sidebar.write('**Select a Location**')
usrLoc = UserLocation()
locationChoice = st.sidebar.selectbox('_placeholder_', usrLoc.locations_list, label_visibility='collapsed')
usrLoc.initialize_location_services(locationChoice)

# Generate passes
def display_results_summary(constObj, usrObject, df):
    st.subheader('Satellite Transit Summary')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Constellation", constObj.constellation)
    col2.metric("Total Satellites Queried", constObj.count)
    col3.metric("Transits", constObj.num_passes)
    col4.metric("Unique Satellites", constObj.unique_assets)
    col1, col2 = st.columns(2)
    col1.metric("Transits Start", usrObject.start_datestr)
    col2.metric("Transits End", usrObject.end_datestr)
    if not df.empty:
        st.caption('Satellite Transit Schedule (all times are in local timezone).')
        st.dataframe(df, use_container_width=True)
    else:
        st.caption('No transists found in the given timeframe.')

# This will cache satellite data so we do not keep making requests to Celestrak
@st.experimental_singleton
def getCachedConstellation(constellationName):
    constellation = const_utils.SatConstellation(constellationName)
    return constellation
constellation = getCachedConstellation(constellationChoice)

# After satellite data is retrieved, compute transits
if constellation.initialized and usrLoc.initialized:
    constellation.generatePasses(usrLoc)
    df = constellation.getSchedule()
    display_results_summary(constellation, usrLoc, df)
else:
    st.error('Will need to fix issues before we can proceed.')

#   3. About Block
st.subheader('**About**')
st.write('''
This tool was co-created by [Prit Chovatiya](https://pritc.space/) and [Michael Levy](https://mplevy.com/) from their shared love of streamlit and passion for satellite constellations. 
''')