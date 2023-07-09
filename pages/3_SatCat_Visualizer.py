import streamlit as st
import plotly.express as px
import requests
# import configparser
import pandas as pd

# Meta Info
st.set_page_config(page_title="SatCat Visualizer")
st.subheader('SatCat Visualizer 🛰 🛰 🛰')
st.caption('''Explore stats such as launch cadence / orbital elements 
distributions for various satellite sets. Group them by launch year, 
orbital status and classification and see insights come to life.
''')

@st.cache(ttl=86400, show_spinner="Fetching data from Spacetrack API...")
def get_data_from_spacetrack(constSelect, query_limit):
    
    def getSiteCred():
        # # Use configparser package to pull in the ini file (pip install configparser) if running app locally
        # config = configparser.ConfigParser()
        # config.read("pages/SLTrack.ini")
        # configUsr = config.get("configuration","username")
        # configPwd = config.get("configuration","password")
        # return {'identity': configUsr, 'password': configPwd}

        # for deployed app on streamlit, use native streamlit method to load secrets
        return {'identity': st.secrets.configuration.username, 'password': st.secrets.configuration.password}

    uriBase                = "https://www.space-track.org"
    requestLogin           = "/ajaxauth/login"
    requestCmdAction       = "/basicspacedata/query" 
    requestURL = requestDict[constSelect] + f"/limit/{query_limit}"

    with requests.Session() as session:
        # need to log in first. note that we get a 200 to say the web site got the data, not that we are logged in
        siteCred = getSiteCred()
        resp = session.post(uriBase + requestLogin, data = siteCred)
        if resp.status_code != 200:
            print("Could not reach Spacetrack!")
        # this query picks up all Starlink satellites from the catalog. Note - a 401 failure shows you have bad credentials
        resp = session.get(uriBase + requestCmdAction + requestURL)  
        if resp.status_code != 200:
            print("API query failed from Spacetrack!")
        else:
            session.close()
        df = pd.read_json(resp.text)
        df['LAUNCH_YEAR'] = "'" + df['INTLDES'].str.slice(0,2)
        df['ALTITUDE'] = df['SEMIMAJOR_AXIS'] - 6378
        df.loc[df["DECAYED"] == 0, "STATUS"] = "In-orbit"
        df.loc[df["DECAYED"] == 1, "STATUS"] = "Decayed"
    return df

requestDict = {
    "STARLINK" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/STARLINK~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "ONEWEB" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/ONEWEB~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "SPIRE" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/LEMUR~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "PLANET" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/SKYSAT~~/OBJECT_NAME/FLOCK~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "SWARM" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/SPACEBEE~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "GEO" : "/class/tle_latest/MEAN_MOTION/0.99--1.01/ORDINAL/1/ECCENTRICITY/%3C0.01/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "MEO" : "/class/tle_latest/MEAN_MOTION/1.8--2.39/ORDINAL/1/ECCENTRICITY/<0.25/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "LEO" : "/class/tle_latest/MEAN_MOTION/>11.25/ORDINAL/1/ECCENTRICITY/<0.25/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "HEO" : "/class/tle_latest/ORDINAL/1/ECCENTRICITY/>0.25/format/json/orderby/NORAD_CAT_ID,EPOCH",
    "GLOBALSTAR" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/GLOBALSTAR~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "INMARSAT" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/INMARSAT~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "INTELSAT" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/INTELSAT~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "IRIDIUM" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/IRIDIUM~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "ORBCOMM" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/OBJECT_NAME/ORBCOMM~~/format/json/orderby/NORAD_CAT_ID%20asc",
    "HUMAN_SPACEFLIGHT": "/class/tle_latest/favorites/Human_Spaceflight/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "AMATUER": "/class/tle_latest/favorites/Amateur/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "NAVIGATION": "/class/tle_latest/favorites/Navigation/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "SPECIAL_INTEREST": "/class/tle_latest/favorites/Special_Interest/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "WEATHER": "/class/tle_latest/favorites/Weather/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "VISIBLE": "/class/tle_latest/favorites/Visible/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "BRIGHT_GEO": "/class/tle_latest/favorites/brightgeo/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc",
    "ALL_OBJECTS" : "/class/tle_latest/NORAD_CAT_ID/>40000/ORDINAL/1/format/json/orderby/NORAD_CAT_ID%20asc"
}

statItem = {
    "Launch Year": "LAUNCH_YEAR",
    "Altitude (km)" : "ALTITUDE", 
    "Inclination (deg)" : "INCLINATION",
    "Eccentricity" : "ECCENTRICITY",
    "RAAN (deg)" : "RA_OF_ASC_NODE", 
    "Arg. of Perigee (deg)" : "ARG_OF_PERICENTER", 
    "Orbital Revolution Number" : "REV_AT_EPOCH", 
    "NORAD ID": "NORAD_CAT_ID", 
    "BSTAR": "BSTAR"
}

groupbyItem = {
    "Launch Year" : "LAUNCH_YEAR",
    "Decay vs Active" : "STATUS", 
    "Classification" : "CLASSIFICATION_TYPE"
}

# UI Elements
# ------------------------- Sidebar panel
# Get user input:
st.sidebar.write('Begin here 👇')
constSelect = st.sidebar.selectbox('Select a constellation', tuple(requestDict.keys()))
query_limit = st.sidebar.slider("Limit number of results upto:", min_value=1000, max_value=21000, value=5000, step=4000)

# Query data from Spacetrack
with st.spinner("Retrieving data from Spacetrack..."):
    df = get_data_from_spacetrack(constSelect, query_limit)
    # st.success(f"Retrieved {df.shape[0]} results.")
    st.sidebar.success(f"Loaded {df.shape[0]} satellites.",icon="✅")

def plot_figures():
    tab1, tab2 = st.tabs(["Distributions", "Tabulated Data"])
    with tab1:
        for choice in statChoices:
            title_str = f"{constSelect}: {choice} distribution for {df.shape[0]} satellites"
            hover_tip={'OBJECT_NAME':True, 'NORAD_CAT_ID':':.0f', 'STATUS':True}
            fig = px.histogram(df, x=statItem[choice], color=groupbyItem[groupChoice], pattern_shape="STATUS" ,marginal="rug", hover_data=hover_tip, title = title_str, pattern_shape_map={"In-orbit": "", "Decayed": "/"})
            st.plotly_chart(fig, theme="streamlit")
    with tab2:
        df_to_show = df.copy()
        df_to_show = df_to_show[['OBJECT_NAME', 'NORAD_CAT_ID', 'INTLDES', 'STATUS', 'EPOCH', 'ALTITUDE', 'PERIOD']]
        df_to_show.rename(columns={
            'OBJECT_NAME': 'ASSET', 
            'NORAD_CAT_ID': 'NORAD_ID',
            'INTLDES': 'INTLDES',
            'STATUS': 'STATUS',
            'EPOCH': 'EPOCH (UTC)', 
            'ALTITUDE': 'ALTITUDE (KM)', 
            'PERIOD': 'PERIOD (MINUTES)'}, errors="raise",inplace = True)
        df_to_show.set_index('ASSET', inplace=True)
        st.dataframe(df_to_show)

groupChoice = st.sidebar.radio('Group by:', tuple(groupbyItem.keys()))
statChoices = st.sidebar.multiselect('Select stat types:', statItem.keys(), ["Launch Year", "Altitude (km)", "Inclination (deg)"])
plot_figures()
