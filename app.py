import streamlit as st
import constellation_utils as const_utils
import location_utils as loc_utils
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
usrLoc = loc_utils.UserLocation()
locationChoice = st.sidebar.selectbox('_placeholder_', usrLoc.locations_list, label_visibility='collapsed')
usrLoc.initialize_location_services(locationChoice)

# Generate passes
def display_results_summary(constObj, usrObject, df):
    st.subheader('Satellite Transit Summary')
    # metric row 1
    col1, col2, col3, col4 = st.columns([1,1,1.5,2.5])
    col1.metric("Transits", constObj.num_passes)
    col2.metric("Satellites", constObj.unique_assets)
    col3.metric("Constellation", constObj.constellation)
    col4.metric(f"{const_utils._MINELEVATIONS[constObj.constellation]}° Above Horizon Over", usrLoc.selected_loc)
    # metric row 2
    col1, col2, col3 = st.columns([4,0.5,2])
    col1.metric("Transits Start + Delta", f'{usrObject.start_datestr} + {loc_utils.DATERANGE_DELTA_DAYS*24}hrs')
    col3.metric("Total Satellites Queried", constObj.count)
    # main table
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.caption(f"Satellite transit schedule for transits over {const_utils._MINELEVATIONS[constObj.constellation]}° of elevation above the horizon (all times are in local timezone of the selected location).")
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
This tool was co-created by [Prit Chovatiya](https://www.linkedin.com/in/prit-chovatiya/) and [Michael Levy](https://www.linkedin.com/in/levymp/) from their shared love of streamlit and passion for satellite constellations. 
''')