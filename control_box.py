import numpy as np
from scipy.integrate import odeint
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta, datetime as dt


# CONSTANTS
# Earth's Gravitational constant (m^3/kg/s^2)
G = 6.67430e-11
# Earth's mass (kg)
M_Earth = 5.972e24
radiusEarth = 6378.137e3 # m
j2Earth = 1.08262668e-3 # harmonic constant
omega = 7.292115e-5 # rotational speed of Earth


# Convert Keplerian elements to Cartesian coordinates
def keplerian_to_cartesian(semi_major_axis, eccentricity, inclination, argument_of_periapsis, longitude_of_ascending_node, true_anomaly):
    a = semi_major_axis
    e = eccentricity
    i = inclination
    w = argument_of_periapsis
    Omega = longitude_of_ascending_node
    nu = true_anomaly

    # Calculate position in perifocal coordinates
    r_pqw = a * (1 - e**2) / (1 + e * np.cos(nu))
    x_pqw = r_pqw * (np.cos(nu + w) * np.cos(Omega) - np.sin(nu + w) * np.sin(Omega) * np.cos(i))
    y_pqw = r_pqw * (np.cos(nu + w) * np.sin(Omega) + np.sin(nu + w) * np.cos(Omega) * np.cos(i))
    z_pqw = r_pqw * (np.sin(nu + w) * np.sin(i))

    # Calculate velocity in perifocal coordinates
    v_pqw = np.sqrt(G * M_Earth / a)  # Magnitude of velocity
    x_dot_pqw = v_pqw * (-np.sin(nu + w) * np.cos(Omega) - np.cos(nu + w) * np.sin(Omega) * np.cos(i))
    y_dot_pqw = v_pqw * (-np.sin(nu + w) * np.sin(Omega) + np.cos(nu + w) * np.cos(Omega) * np.cos(i))
    z_dot_pqw = v_pqw * (np.cos(nu + w) * np.sin(i))

    return np.array([x_pqw, y_pqw, z_pqw, x_dot_pqw, y_dot_pqw, z_dot_pqw])

class StateVector(object):
    '''
    Stores state object with times
    '''
    def __init__(self, state, time):
        x, y, z, vx, vy, vz = state[0], state[1], state[2], state[3], state[4], state[5]
        self.pos = np.array([x, y, z])
        self.vel = np.array([vx, vy, vz])
        self.elements = np.array([x, y, z, vx, vy, vz]) 
        self.epoch = time

class Propagator():
    '''
    Object that contains info about a satellite object and transit events
    '''
    def __init__(self, force_model_dict):
        self.earth_force = force_model_dict["earth"]
        self.j2_force = force_model_dict["j2"]
        self.drag_force = force_model_dict["drag"]
        self.input_force = force_model_dict["input"]
        self.states = []
        self.prop_state_df = None

    def propagate(self, state, t):
    # Define the state differential equations for Cartesian coordinates
        def drag_forces(ax, ay, az, constant=True):
            # Simple atmosphere model (Exponential model)
            def atmospheric_density(altitude):
                # http://www.braeunig.us/space/atmos.htm#table3
                h0 = 8400  # Scale height (m)
                rho0 = 1.225  # Sea-level density (kg/m^3)
                return rho0 * np.exp(-altitude / h0)
            if not constant:
                densityEarth = atmospheric_density(r - radiusEarth)
            densityEarth = 4.89e-13 # kg/m3
            v_rel_x, v_rel_y, v_rel_z = vx + omega*y, vy - omega*x, vz
            v_rel = np.array([v_rel_x, v_rel_y, v_rel_z])
            drag_force = -0.5*(craft_Cd*craft_area/craft_mass)*densityEarth*v*v_rel
            ax_drag, ay_drag, az_drag = drag_force[0], drag_force[1], drag_force[2]
            return [ax + ax_drag, ay + ay_drag, az + az_drag]       

        def earth_gravitation(ax, ay, az):
            ax_earth = -G * M_Earth * x / r**3
            ay_earth = -G * M_Earth * y / r**3
            az_earth = -G * M_Earth * z / r**3
            return [ax + ax_earth, ay + ay_earth, az + az_earth]

        def j2_pertubation(ax, ay, az):
            # Ref: Analytical Mechanics of Space Systems pp. 379-390
            # Gravitational acceleration due to the Earth's oblateness (J2 perturbation)
            J2_perturbation = -3/2 * j2Earth * (M_Earth*G / r**2) * (radiusEarth**2 / r**2)
            ax_j2 = J2_perturbation * (x / r) * (1 - 5 * (z/r)**2)
            ay_j2 = J2_perturbation * (y / r) * (1 - 5 * (z/r)**2)
            az_j2 = J2_perturbation * (z / r) * (3 - 5 * (z/r)**2)
            return [ax + ax_j2, ay + ay_j2, az + az_j2]
        
        def input_forces(ax, ay, az):
            ax_in, ay_in, az_in = 0.0, 0.0, 0.0
            return [ax + ax_in, ay + ay_in, az + az_in]
        
        def compute_forces():
            # initialize forces
            ax, ay, az = 0.0, 0.0, 0.0
            if self.earth_force:
                ax, ay, az = earth_gravitation(ax, ay, az)
            if self.j2_force:
                ax, ay, az = j2_pertubation(ax, ay, az)
            if self.drag_force:
                ax, ay, az = drag_forces(ax, ay, az)
            if self.input_force:
                ax, ay, az = input_forces(ax, ay, az)
            return [ax, ay, az]

        x, y, z, vx, vy, vz = state
        r = np.linalg.norm([x, y, z])
        v = np.linalg.norm([vx, vy, vz])
        ax, ay, az = compute_forces()
        return [vx, vy, vz, ax, ay, az]

    def plot_states(self, ode_result, time_nodes):
        # ode_result should be shape: (NUM_TIME_NODES, 6)
        states_list = []
        if not len(ode_result):
            st.error("No states returned, not plotting anything.")
        else:
            for id, state in enumerate(ode_result):
                states_list.append(StateVector(state, time_nodes[id]))
            self.states = states_list

            # Extract position and velocity vectors
            x, y, z, vx, vy, vz = ode_result.T

            # Create a Plotly 3D scatter plot
            fig = px.scatter_3d(x=x, y=y, z=z, labels={'x': 'X', 'y': 'Y', 'z': 'Z'})
            fig.update_layout(title=f"Satellite Orbit",scene_aspectmode='cube')
            st.plotly_chart(fig, theme="streamlit")
            
            pd_df_plot = pd.DataFrame(data={"x": x, "y": y, "z": z, "vx": vx, "vy": vy, "vz": vz, "epoch": time_nodes})
            pd_df_plot['x_time_ticks'] = [f"{str(timedelta(seconds=int(time_node)))}" for time_node in time_nodes]
            self.prop_state_df = pd_df_plot # save for future use
            fig = go.Figure()
            fig.add_trace(go.Scatter(x = pd_df_plot['x_time_ticks'], y = pd_df_plot['x'] / 1000, name='X', mode='lines'))
            fig.add_trace(go.Scatter(x = pd_df_plot['x_time_ticks'], y = pd_df_plot['y'] / 1000, name='Y', mode='lines'))
            fig.add_trace(go.Scatter(x = pd_df_plot['x_time_ticks'], y = pd_df_plot['z'] / 1000, name='Z', mode='lines'))
            fig.update_layout(  title_text = "ECI States", xaxis = {'title': 'Epoch (s)', 'ticktext': pd_df_plot['x_time_ticks']}, 
                                yaxis = {'title': 'State Component (km)'}, hovermode = 'x unified')
            st.plotly_chart(fig, theme="streamlit")

def forced_prop_model(state, t, prop1, prop2):
    '''
    state is made up of two seperate states:
        state_reference (m1): [m1_x, m1_y, m1_z, m1_vx, m1_vy, m1_vz]
        state_forced (m2): [m2_x, m2_y, m2_z, m2_vx, m2_vy, m2_vz]
        state ([m1 m2]): [m1_x, m1_y, m1_z, m1_vx, m1_vy, m1_vz, m2_x, m2_y, m2_z, m2_vx, m2_vy, m2_vz]
    '''
    
    def compute_input_forces(ax, ay, az):

        def unit_vector(vec):
            return vec / np.linalg.norm(vec)

        def r_transform(state_array):
            # Inertial to RIC transformation matrix w.r.t to state 1
            r_vec, v_vec = state_array[0:3], state_array[3:6]
            h_vec = np.cross(r_vec, v_vec)
            r_hat = unit_vector(r_vec)
            c_hat = unit_vector(h_vec)
            i_hat = np.cross(c_hat, r_hat)
            return np.array([r_hat, i_hat, c_hat])
        
        # inertial state difference
        diff = state[6:] - state[0:6] # state 2 (drag + dmu perturbed) - state 1 (reference)
        eci_to_ric = r_transform(state[0:6]) # get ric tranformation matrix
        delta_ric = np.dot(eci_to_ric, diff[:3]) # get tranform matrix w.r.t model 1 
        # convert force from RIC to ECI using transpose of tranformation matrix
        force_mag = 1e-5*np.array([0, 2, 0]) # in-track thruster default
        # force_mag = np.array([0, 2, 0]) # in-track thruster default
        r_miss, i_miss, c_miss = delta_ric[0], delta_ric[1], delta_ric[2]
        
        if i_miss > 4500:
            # print(f"time: {t}, radial: {r_miss}, in-track miss: {i_miss}")
            force_eci_vec =  np.dot(eci_to_ric.T, force_mag)
            ax_in, ay_in, az_in = force_eci_vec[0], force_eci_vec[1], force_eci_vec[2]
        else:
            # apply no force if inside control box
            ax_in, ay_in, az_in = 0.0, 0.0, 0.0
        return [ax + ax_in, ay + ay_in, az + az_in]
    
    m1_vx, m1_vy, m1_vz, m1_ax, m1_ay, m1_az = prop1.propagate(state[0:6], t)
    m2_vx, m2_vy, m2_vz, m2_ax, m2_ay, m2_az = prop2.propagate(state[6:], t)

    # add input force on model 2
    m2_ax_dv, m2_ay_dv, m2_az_dv = compute_input_forces(m2_ax, m2_ay, m2_az)

    combined_state = np.array([m1_vx, m1_vy, m1_vz, m1_ax, m1_ay, m1_az, m2_vx, m2_vy, m2_vz, m2_ax_dv, m2_ay_dv, m2_az_dv])

    return combined_state

def compare_props(prop1, prop2):

    def unit_vector(vec):
        return vec / np.linalg.norm(vec)

    def r_transform(state):
        # Inertial to RIC transformation matrix
        r_vec = state.pos
        v_vec = state.vel
        h_vec = np.cross(r_vec, v_vec)
        r_hat = unit_vector(r_vec)
        c_hat = unit_vector(h_vec)
        i_hat = np.cross(c_hat, r_hat)
        return np.array([r_hat, i_hat, c_hat])
    
    def get_ric_vectors():
        r_list, i_list, c_list = [], [], []
        for state1, state2 in zip(prop1.states, prop2.states):
            # print(np.shape(state1))
            # print(np.shape(state2))
            diff = state2.elements - state1.elements
            delta_ric = np.dot(r_transform(state1), diff[:3])
            r_list.append(delta_ric[0])
            i_list.append(delta_ric[1])
            c_list.append(delta_ric[2])
        return r_list, i_list, c_list
    
    # Plot ECI state differences
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x = prop1.prop_state_df['x_time_ticks'], y = (prop2.prop_state_df['x'] - prop1.prop_state_df['x']), name='dX', mode='lines'))
    fig1.add_trace(go.Scatter(x = prop1.prop_state_df['x_time_ticks'], y = (prop2.prop_state_df['y'] - prop1.prop_state_df['y']), name='dY', mode='lines'))
    fig1.add_trace(go.Scatter(x = prop1.prop_state_df['x_time_ticks'], y = (prop2.prop_state_df['z'] - prop1.prop_state_df['z']), name='dZ', mode='lines'))
    fig1.update_layout(title_text = "ECI State Difference", xaxis = {'title': 'Epoch (s)'}, yaxis = {'title': 'Delta State Component (m)'}, hovermode = 'x unified')
    st.plotly_chart(fig1, theme="streamlit")
    
    # Get RIC state difference w.r.t to primary (model-1) object
    r_list, i_list, c_list = get_ric_vectors()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x = prop1.prop_state_df['x_time_ticks'], y = r_list, name='R', mode='lines'))
    fig2.add_trace(go.Scatter(x = prop1.prop_state_df['x_time_ticks'], y = i_list, name='I', mode='lines'))
    fig2.add_trace(go.Scatter(x = prop1.prop_state_df['x_time_ticks'], y = c_list, name='C', mode='lines'))
    fig2.update_layout(title_text = "RIC State Difference", xaxis = {'title': 'Epoch (s)'}, yaxis = {'title': 'Delta State Component (m)'}, hovermode = 'x unified')
    st.plotly_chart(fig2, theme="streamlit")
    st.text("The RIC state differences are with respect to Model 1.")

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x = i_list, y = r_list, name='R', mode='lines'))
    fig3.add_vline(x=5000, line_width=1, line_dash="dash", line_color="red")
    fig3.update_layout(title_text = "Radial v In-track State Difference", xaxis = {'title': 'In-track (m)'}, yaxis = {'title': 'Radial (m)'}, hovermode = 'x unified')
    st.plotly_chart(fig3, theme="streamlit")


# Inputs
# --------------------------
# initial orbit
a = 6778.137e3 # semimajor axis (m)
e = 1e-3 # eccentricity
i = 33 # inclination (degree)
argPeri = 90 # argument of perigee (degree)
trueAnomaly = 0 # true anomaly (degree)
RAAN = 0 # right ascesion of ascending node

# spacecraft tweeks 
craft_area = 10 # area m2
craft_mass = 500 # mass kg
craft_Cd = 2.2 # coefficient of drag

# --------------------------

# Start the app
st.title("Satellite Orbit Propagation")
st.sidebar.header("Orbital Parameters")
# Print keplerian elements
st.sidebar.text(f"semimajor axis (m): {a}")
st.sidebar.text(f"eccentricity: {e}")
st.sidebar.text(f"inclination (degree): {i}")
st.sidebar.text(f"right ascesion of ascending node: {RAAN}")
st.sidebar.text(f"true anomaly (degree): {trueAnomaly}")
st.sidebar.text(f"argument of perigee (degree): {argPeri}")
# Convert Keplerian elements to Cartesian initial state
initial_state_keplerian = np.array([a, e, i, argPeri, RAAN, trueAnomaly])
initial_state_cartesian = keplerian_to_cartesian(*initial_state_keplerian)
# Print ECI coordinates
st.sidebar.write("---")
st.sidebar.header("Inertial State")
st.sidebar.text(f"ECI pos (x, y, z) [km]: {[round(state/1e3, 2) for state in initial_state_cartesian[:3]]}")
st.sidebar.text(f"ECI pos (vx, vy, vz) [km/s]: {[round(state/1e3, 2) for state in initial_state_cartesian[3:]]}")
st.sidebar.text(f"Initial Altitude [km]: {round((np.linalg.norm(initial_state_cartesian[:3]) - radiusEarth)/1e3, 2)}")
st.sidebar.text(f"Initial Velocity [km/s]: {round(np.linalg.norm(initial_state_cartesian[3:])/1e3, 2)}")
# Get time inputs
col1, col2 = st.columns(2)
time_delta = col1.slider("Time range (days):", min_value=1, max_value=4, value=3, step=1) # get simulation time range
time_step_dict = {"1s": 1, "10s": 10, "30s": 30, "1m": 60, "1hr": 60*60}
time_step = col2.selectbox("Time step:", options=time_step_dict.keys()) # get time step
t_span = np.arange(0, time_delta * 3600 * 24, time_step_dict[time_step]) # get time vector
st.text(f"Using {len(t_span)} equaly space points: [T0s, T+{t_span[1]}s, ..., T+{t_span[-1]}s].")

# Configure force models
fm1_input = {"earth": True, "j2": True, "drag": False, "input": False}
prop1 = Propagator(fm1_input) # initialize propagator from model 1 inputs
fm2_input = {"earth": True, "j2": True, "drag": True, "input": True}
prop2 = Propagator(fm2_input) # initialize propagator from model 2 inputs
# Report model definitions
st.text(f"Model 1:\nGravity Earth: {prop1.earth_force} | J2: {prop1.j2_force} | Drag: {prop1.drag_force} | DMU Input Force: {prop1.input_force}")
st.text(f"Model 2:\nGravity Earth: {prop2.earth_force} | J2: {prop2.j2_force} | Drag: {prop2.drag_force} | DMU Input Force: {prop2.input_force}")

# Propagate the orbit using numerical integration
combined_initial_state = list(initial_state_cartesian) + list(initial_state_cartesian)
F_rez = odeint(forced_prop_model, np.array(combined_initial_state), t_span, args=(prop1, prop2))

tab1, tab2, tab3 = st.tabs(["Model 1", "Model 2", "Diffs"])
# Show results and pretty pictures
with tab1:
    prop1.plot_states(F_rez.T[0:6].T, t_span)
with tab2:
    prop2.plot_states(F_rez.T[6:].T, t_span)
with tab3:
    if prop1.earth_force == prop2.earth_force and prop1.j2_force == prop2.j2_force and prop1.drag_force == prop2.drag_force:
        st.warning("Both force models are configured exactly the same. There will be no difference in propagation results.")
        st.warning('Toggle "Atmospheric Drag forces" in Model 2 to see the difference.')
    else:
        compare_props(prop1, prop2)
