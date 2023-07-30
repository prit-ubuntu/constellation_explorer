import streamlit as st
import plotly.express as px
import requests
import pandas as pd
from satcat_configs import requestDict, statItems, groupbyItems

# Meta Info
st.set_page_config(page_title="SatCat Visualizer")
st.subheader('SatCat Visualizer 🛰 🛰 🛰')
st.caption('''Explore stats such as launch cadence / orbital elements 
distributions for various satellite sets. Group them by launch year, 
orbital status and classification and see insights come to life.
''')

@st.cache(ttl=86400)
def get_data_from_spacetrack(constSelect, query_limit):
    
    def getSiteCred():
        # use file in .streamlit/secrets.toml when running locally / else deployed streamlit app needs those secrets defined
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
            st.error("Could not reach Spacetrack!")
        # make get request from Spacetrack using the URL + auth
        resp = session.get(uriBase + requestCmdAction + requestURL)  
        if resp.status_code != 200:
            st.error("API query failed from Spacetrack!")
        else:
            session.close()
        df = pd.read_json(resp.text)
        # sanitize data - needs to be in this function for cacheing to work
        df['LAUNCH_YEAR'] = "'" + df['INTLDES'].str.slice(0,2)
        df['ALTITUDE'] = df['SEMIMAJOR_AXIS'] - 6378
        df.loc[df["DECAYED"] == 0, "STATUS"] = "In-orbit"
        df.loc[df["DECAYED"] == 1, "STATUS"] = "Decayed"
    return df

# UI Elements
# ------------------------- Sidebar panel
# Get user input:
st.sidebar.write('Begin here 👇')
constSelect = st.sidebar.selectbox('Select a constellation', tuple(requestDict.keys()))
query_limit = st.sidebar.slider("Limit number of results upto:", min_value=1000, max_value=21000, value=5000, step=4000)

# Query data from Spacetrack
with st.spinner("Retrieving data from Spacetrack..."):
    df = get_data_from_spacetrack(constSelect, query_limit)

    # report progress
    st.sidebar.success(f"Loaded {df.shape[0]} satellites.",icon="✅")

def plot_figures():
    tab1, tab2 = st.tabs(["Distributions", "Tabulated Data"])
    with tab1:
        for choice in statChoices:
            title_str = f"{constSelect}: {choice} distribution for {df.shape[0]} satellites"
            hover_tip={'OBJECT_NAME':True, 'NORAD_CAT_ID':':.0f', 'STATUS':True}
            fig = px.histogram(df, x=statItems[choice], color=groupbyItems[groupChoice], pattern_shape="STATUS" ,marginal="rug", hover_data=hover_tip, title = title_str, pattern_shape_map={"In-orbit": "", "Decayed": "/"})
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

groupChoice = st.sidebar.radio('Group by:', tuple(groupbyItems.keys()))
statChoices = st.sidebar.multiselect('Select stat types:', statItems.keys(), list(statItems.keys())[0:3])
plot_figures()
