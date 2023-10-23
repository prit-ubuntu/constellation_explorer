import streamlit as st
from skyfield.api import load, wgs84, EarthSatellite
import satellite_utils as st_utils
from datetime import (datetime as dt, timedelta)
from pytz import timezone
import requests
import constellation_configs as cc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

DT_FORMAT = '%b %d, %Y %H:%M:%S'

def compare_sats(sat1df, sat2df):

    def unit_vector(vec):
        return vec / np.linalg.norm(vec)

    def r_transform(state):
        if len(state) == 6:
            # Inertial to RIC transformation matrix
            r_vec, v_vec = state[0:3], state[-3:]
            h_vec = np.cross(r_vec, v_vec)
            r_hat = unit_vector(r_vec)
            c_hat = unit_vector(h_vec)
            i_hat = np.cross(c_hat, r_hat)
            return np.array([r_hat, i_hat, c_hat])
        else:
            raise Exception("Cannot do RIC transform with len(state) is not 6!")
    
    def get_ric_vectors():
        r_list, i_list, c_list = [], [], []
        for (idxRow, s1), (_, s2) in zip(sat1df.iterrows(), sat2df.iterrows()):
                state1 = np.array([s1['x'], s1['y'], s1['z'], s1['vx'], s1['vy'], s1['vz']])
                state2 = np.array([s2['x'], s2['y'], s2['z'], s2['vx'], s2['vy'], s2['vz']])
                diff =  state2 - state1
                delta_ric = np.dot(r_transform(state1), diff[:3])
                r_list.append(delta_ric[0])
                i_list.append(delta_ric[1])
                c_list.append(delta_ric[2])
        return r_list, i_list, c_list
    
    # # Get RIC state difference w.r.t to primary (model-1) object 
    r_list, i_list, c_list = get_ric_vectors()
    st1df['r_miss'], st1df['i_miss'], st1df['c_miss'] = r_list, i_list, c_list
    miss_mags = [np.linalg.norm(np.array([r_miss, i_miss, c_miss])) for r_miss, i_miss, c_miss in zip(r_list, i_list, c_list)]
    st1df['miss_mags'] = miss_mags
    subtitle_str = f"<br><sup>{satObject2.satrec_object.name} ({satObject2.satrec_object.model.satnum}) w.r.t {satObject1.satrec_object.name} ({satObject1.satrec_object.model.satnum})</sup>"
    
    st.info(f"The RIC differences are with respect to the primary satellite: {option1}", icon="ℹ️")
    tab1, tab2 = st.tabs(["Miss Distances (RIC)", "Planar Projections (RIC)"])

    with tab1:
        # # Plot RIC - 3D 
        fig_3d_ric = go.Figure()
        fig_3d_ric.add_trace(go.Scatter3d(x = st1df['r_miss'], y = st1df['i_miss'], z = st1df['c_miss'], mode="lines"))
        scene_dict = {'xaxis': {'title': 'Radial (m)'},
                        'yaxis': {'title': 'In-track (m)'}, 
                        'zaxis': {'title': 'Cross-track (m)'}}
        margin_dict = {'l': 0, 'r': 0, 'b': 0, 't': 0}
        camera_dict = dict(
            up=dict(x=0, y=0, z=1),
            center=dict(x=0, y=0, z=0),
            eye=dict(x=-1.25, y=-1.25, z=1.25)) 
        fig_3d_ric_title = f"Overall Miss Distance {subtitle_str}"
        fig_3d_ric_layout = go.Layout(title_text = fig_3d_ric_title,
                                        margin=margin_dict, scene=scene_dict, scene_camera=camera_dict)
        fig_3d_ric.update_layout(fig_3d_ric_layout)        
        st.plotly_chart(fig_3d_ric, theme="streamlit")
        
        # # Plot RIC miss magnitude
        fig_miss_mag = go.Figure()
        fig_miss_mag.add_trace(go.Scatter(x = st1df['epoch'], y = st1df['miss_mags'], name='Overall Miss (m)', mode="lines"))
        fig_miss_mag.update_layout(title_text = f"Overall Miss Distance {subtitle_str}", xaxis = {'title': 'Date'}, yaxis = {'title': 'Overall Miss (m)'}, hovermode = 'x unified')
        st.plotly_chart(fig_miss_mag, theme="streamlit")
        
        # # Plot RCI state differences
        fig_ric = go.Figure()
        fig_ric.add_trace(go.Scatter(x = st1df['epoch'], y = st1df['r_miss'], name='Radial Miss (m)', mode='lines', yaxis="y1", hovertemplate = '%{y:.2f}'))
        fig_ric.add_trace(go.Scatter(x = st1df['epoch'], y = st1df['i_miss'], name='In-track Miss (m)', mode='lines', yaxis="y2", hovertemplate = '%{y:.2f}'))
        fig_ric.add_trace(go.Scatter(x = st1df['epoch'], y = st1df['c_miss'], name='Cross-track Miss (m)', mode='lines', yaxis="y3", hovertemplate = '%{y:.2f}'))
        fig_ric.update_layout(
            # xaxis = {'title': 'Date', 'domain': [0.25, 0.9], 'tickformat' : '%Y-%m-%dT%H:%M:%SZ'},
            xaxis = {'title': 'Date', 'tickformat' : '%Y-%m-%dT%H:%M:%SZ'},
            yaxis1  = {'title': {'text': 'Radial Miss (m)', 'standoff': 1}, 'side': 'left', 'autoshift': True, 'anchor': 'free', 'position': 0.1},
            yaxis2 = {'title': {'text': 'In-track Miss (m)', 'standoff': 1}, 'side': 'left', 'overlaying': 'y1', 'autoshift': True, 'position': 0.2},
            yaxis3 = {'title': {'text': 'Cross-track Miss (m)', 'standoff': 15} , 'side': 'right', 'overlaying': 'y1', 'autoshift': True, 'position': 0.9},
            hovermode = 'x unified',
            legend = {'orientation' : 'h', 'xanchor': 'right', 'x': 1, 'yanchor': 'bottom', 'y': -1},
            title_text=f"RIC State Difference {subtitle_str}")
        st.plotly_chart(fig_ric, theme="streamlit")

    with tab2:
        # # 2. Plot In-Track-Cross-Track Plane
        fig_r_i = go.Figure()
        fig_r_i.add_trace(go.Scatter(x = st1df['i_miss'], y = st1df['c_miss'], name='R', mode="lines"))
        # fig_r_i.add_vline(x=5000, line_width=1, line_dash="dash", line_color="red")
        fig_r_i.update_layout(title_text = f"In-Track-Cross-Track Plane {subtitle_str}", xaxis = {'title': 'In-track (m)'}, yaxis = {'title': 'Cross-track (m)'}, hovermode = 'x unified')
        st.plotly_chart(fig_r_i, theme="streamlit")
        # # 3. Plot Radial-Cross-Track Plane
        fig_r_i = go.Figure()
        fig_r_i.add_trace(go.Scatter(x = st1df['r_miss'], y = st1df['c_miss'], name='R', mode="lines"))
        # fig_r_i.add_vline(x=5000, line_width=1, line_dash="dash", line_color="red")
        fig_r_i.update_layout(title_text = f"Radial-Cross-Track Plane {subtitle_str}", xaxis = {'title': 'Radial (m)'}, yaxis = {'title': 'Cross-track (m)'}, hovermode = 'x unified')
        st.plotly_chart(fig_r_i, theme="streamlit")
        # # 4. Plot In-Track-Radial Plane
        fig_r_i = go.Figure()
        fig_r_i.add_trace(go.Scatter(x = st1df['i_miss'], y = st1df['r_miss'], name='R', mode="lines"))
        # fig_r_i.add_vline(x=5000, line_width=1, line_dash="dash", line_color="red")
        fig_r_i.update_layout(title_text = f"In-Track-Radial Plane {subtitle_str}", xaxis = {'title': 'In-track (m)'}, yaxis = {'title': 'Radial (m)'}, hovermode = 'x unified')
        st.plotly_chart(fig_r_i, theme="streamlit")


# UI Elements
# ------------------------- Sidebar panel
# Get user input:
st.sidebar.write('Begin here 👇')

# 1. Select a group of satellites
@st.cache_resource(ttl=21600)
def query_sats(sat_group):
    _URL = 'http://celestrak.com/NORAD/elements/'
    url = f'{_URL}{cc.TLE_GROUP_URL[sat_group]}.txt'
    return load.tle_file(url)

def get_satellites():
    satellite_group_type = st.sidebar.selectbox('Select a satellite group:', tuple(cc.TLE_GROUP_URL))
    satellites = query_sats(satellite_group_type)
    return satellites

satellites = get_satellites()
st.sidebar.success(f"Loaded {len(satellites)} satellites.",icon="✅")

# 2. Get Date Range
start_time = dt.utcnow().replace(tzinfo=timezone('UTC'))
dateOptStart = dt(start_time.year, start_time.month, start_time.day, start_time.hour, 0, 0, 0, timezone('UTC'))
dateChoice = st.sidebar.slider(
    f"Select time range (UTC):",
    min_value = dateOptStart,
    max_value = dateOptStart + timedelta(days=2),
    value=(dateOptStart, dateOptStart + timedelta(hours=18)),
    step = (timedelta(minutes=120)),
    format = "MM/DD HH:mm")

# 3. Select satellite of interest
by_name = {f"{sat.model.satnum:<6} | {sat.name}": sat for sat in satellites}
col1, col2 = st.columns([1,1])
with col1:
    option1 = st.selectbox('Select primary satellite:', tuple(by_name), index=3)
    satObject1 = st_utils.Satellite(by_name[str(option1)])
    satObject1.results_for_rpo(dateChoice)
    st1df = satObject1.ephemeris.get_df_with_fields()
    st.caption(f'''{satObject1.tle_epoch_str}  
                {satObject1.tle_age_str}''')
with col2:
    option2 = st.selectbox('Select secondary satellite:', tuple(by_name))
    satObject2 = st_utils.Satellite(by_name[str(option2)])
    satObject2.results_for_rpo(dateChoice)
    st2df = satObject2.ephemeris.get_df_with_fields()
    st.caption(f'''{satObject2.tle_epoch_str}  
                {satObject2.tle_age_str}''')

# # show results
compare_sats(st1df, st2df)
