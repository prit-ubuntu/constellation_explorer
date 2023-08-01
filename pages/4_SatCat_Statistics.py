import streamlit as st
import plotly.express as px
import requests
import pandas as pd
from datetime import datetime as dt

# Meta Info
st.set_page_config(page_title="SatCat Statistics")
st.subheader('SatCat Statistics 📈📈📈')
st.caption('''Explore stats for all catalogued objects launched between any selected year range. 
There are three visualizations for this data: 1. Launch + Decay Timelines | 2. Object breakdown by Country, Launch Site, Object Type, Decay Status, RCS size. 
| 3. Composite sunburst chart that shows hierarchical classifications of objects by country, active/decay status and object type. 
''')

@st.cache(ttl=86400, show_spinner="Fetching data from Spacetrack API...")
def get_data_from_spacetrack(year_limit=(2000, 2023)):
    
    def getSiteCred():
        # use file in .streamlit/secrets.toml when running locally / else deployed streamlit app needs those secrets defined
        return {'identity': st.secrets.configuration.username, 'password': st.secrets.configuration.password}

    uriBase                = "https://www.space-track.org"
    requestLogin           = "/ajaxauth/login"
    requestCmdAction       = "/basicspacedata/query" 
    launch_requestURL = f"/class/satcat/LAUNCH_YEAR/{year_limit[0]}--{year_limit[1]}/CURRENT/Y/format/json/orderby/LAUNCH%20desc"
    launchsite_requestURL = "/class/launch_site/format/json/orderby/SITE_CODE%20asc"

    with requests.Session() as session:
        # need to log in first. note that we get a 200 to say the web site got the data, not that we are logged in
        siteCred = getSiteCred()
        resp = session.post(uriBase + requestLogin, data = siteCred)
        if resp.status_code != 200:
            print("Could not reach Spacetrack!")
        resp_launch = session.get(uriBase + requestCmdAction + launch_requestURL)
        if resp_launch.status_code != 200:
            print("API query failed from Spacetrack!")
        else:
            df = pd.read_json(resp_launch.text)
            resp_sites = session.get(uriBase + requestCmdAction + launchsite_requestURL)
            if resp_sites.status_code != 200:
                print("Not using site code to site name mapping.")
            else:
                df_site_map = pd.read_json(resp_sites.text)
                site_dict = dict(zip(df_site_map['SITE_CODE'], df_site_map['LAUNCH_SITE']))
                site_dict = {key: f"{value} ({key})" for key, value in site_dict.items()}
                df['SITE'].replace(site_dict, inplace=True)
                df['DECAY_STATUS'] = df.notna()['DECAY']
                df.loc[df["DECAY_STATUS"] == 0, "DECAY_STATUS"] = "In-orbit"
                df.loc[df["DECAY_STATUS"] == 1, "DECAY_STATUS"] = "Decayed"
        session.close()
        return df
    return None


def plot_distributions(df, singleGroupChoices, compositeGroupChoices, year_limit):

    tab1, tab2, tab3, tab4 = st.tabs(["Timelines", "Groupings", "Hierarchical Groupings", "Raw Data"])

    # Histograms
    with tab1:
        # Luanch distribution default 
        subtitle_str = f"<br><sup>Showing results for {df.shape[0]} satellites launched between {df['LAUNCH'].min()} & {df['LAUNCH'].max()} </sup>"
        title_str = f"Object Counts by Launch Year {subtitle_str}"
        hover_tip={'SATNAME':True, 'NORAD_CAT_ID':':.0f', 'OBJECT_TYPE':True}
        launch_fig = px.histogram(df, x='LAUNCH_YEAR', color='OBJECT_TYPE', hover_data=hover_tip, title=title_str)
        st.plotly_chart(launch_fig, theme="streamlit")
        # Decay distribution default
        title_str = f"Object Counts by Decay Year {subtitle_str}"
        hover_tip={'SATNAME':True, 'NORAD_CAT_ID':':.0f', 'OBJECT_TYPE':True}
        num_bins = (year_limit[1] - year_limit[0]) + 1
        decay_fig = px.histogram(df, x='DECAY', color='OBJECT_TYPE', hover_data=hover_tip, title=title_str, nbins=num_bins)
        st.plotly_chart(decay_fig, theme="streamlit")
    
    # Singlular Grouping Charts
    with tab2:
        if singleGroupChoices:
            for choice in singleGroupChoices:
                df_objecttype = df.copy()
                df_dict = df_objecttype[singular_groupings[choice]].value_counts().to_dict()
                df_objecttype_plot = pd.DataFrame(data = {singular_groupings[choice]: df_dict.keys(), 'OBJECT COUNT': df_dict.values()})
                title_str = f"Object Counts by {choice} {subtitle_str}"
                fig = px.pie(df_objecttype_plot, values=df_objecttype_plot['OBJECT COUNT'], names=singular_groupings[choice], title=title_str)
                fig.update_traces(textposition='inside')
                fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
                st.plotly_chart(fig, theme="streamlit")
        else:
            st.warning("Please select groupings to see plots.")
    
    # Hierarchicial Grouping Charts
    with tab3:
        if compositeGroupChoices:
            for group in compositeGroupChoices:
                title_str = f"{group} {subtitle_str}"
                fig = px.sunburst(df, path=sunburst_groupings[group], title=title_str)
                fig.update_traces(textinfo="label+percent parent")
                st.plotly_chart(fig, theme="streamlit")
                if group == "Objects Overview":
                    with st.expander("How do I interpret this?"):
                        st.caption('''
                                    For instance, the above chart can be used to answer the following question: How many pieces of debris from USA are in-orbit between year X and Y?
                                    Answer: Start by selecting "US" in the central pie, and then selecting "In-orbit" and then hovering over "DEBRIS" to obtain object count.''')
        else:
            st.warning("Please select hierarchical groupings to see plots.")
    
    # Raw Data
    with tab4:
        df_to_show = df[['SATNAME', 'NORAD_CAT_ID', 'COUNTRY', 'OBJECT_TYPE', 'LAUNCH', 'SITE', 'PERIOD', 'INCLINATION', 'PERIGEE', 'APOGEE', 'LAUNCH_NUM', 'DECAY', 'RCS_SIZE']]
        df_to_show.set_index('NORAD_CAT_ID', inplace=True)
        st.dataframe(df_to_show)

    return None

# Normal groupings
singular_groupings = {
    "Country" : "COUNTRY",
    "Object Type" : "OBJECT_TYPE", 
    "Launch Site" : "SITE",
    "In-orbit vs Decayed": "DECAY_STATUS",
    "Radar Cross Section": "RCS_SIZE"
}

# Hierarchical groupings
sunburst_groupings = {
    "Objects Overview": ['COUNTRY', 'DECAY_STATUS', 'OBJECT_TYPE'],
    "Object Type by Country" : ['OBJECT_TYPE', 'COUNTRY'],
    "Decay Status by Country" : ['DECAY_STATUS', 'COUNTRY'],
    "Decay Status by Object Type": ['DECAY_STATUS', 'OBJECT_TYPE']
}

# UI Elements
# ------------------------- Sidebar panel
# Get user input:
st.sidebar.write('Begin here 👇')
year_limit = st.sidebar.slider("Select time range:", min_value=1957, max_value=2023, value=tuple([2010,2023]), step=1)
groupChoice = st.sidebar.multiselect('Groupings by:', singular_groupings.keys(), list(singular_groupings.keys())[0:3])
hierarchyChoice = st.sidebar.multiselect('Hierachical groupings by:', sunburst_groupings.keys(), list(sunburst_groupings.keys()))

# Query data from Spacetrack and display stats
with st.spinner("Retrieving data from Spacetrack..."):
    try:
        df=get_data_from_spacetrack(year_limit)
        st.sidebar.success(f"Loaded {df.shape[0]} satellites.",icon="✅")
        plot_distributions(df, groupChoice, hierarchyChoice, year_limit)
    except:
        st.error("Uh oh, something went horribly wrong 😔")
