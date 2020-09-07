import pandas as pd
import streamlit as st
from math import pi, sqrt
from collections import defaultdict

# # Michael Levy 9/7/2020
# SpaceX Interview followup



# Set title
st.title('Orbital Elements Calculation')

# Initial Given Values
st.write('Given Values')
# Dictionary of Values -> Pandas DataFrame
oe = {'apogee': 200, 'perigee': 100, 'inclination': 90, 'argument of perigee': 270}
given = pd.DataFrame(oe, index=['VALUE']).transpose()
# Append Units
units = ['km', 'km', 'deg', 'deg']
given['UNITS'] = units
# Display values
st.write(given)
# Show known constants
st.write('Known Constants')
known = pd.DataFrame({'Radius of Earth': 6378, 'Gravitational Parameter': 398600}, index=['VALUE']).transpose()
# Append Units
known['UNITS'] = ['km', 'km^3/s^2']
# Display Values
st.write(known)

# Set local variables
# Radius of Earth
R = known['VALUE']['Radius of Earth']  # km
# Gravitational Parameter
mu = known['VALUE']['Radius of Earth']  # km^3/s^2


def main():
    # New dataframe for calculated values assign -> {value, units}
    calc = pd.DataFrame(index=['UNITS', 'VALUE'])
    # Assign radius of apogee and perigee
    calc['r_apogee'] = {R + oe['apogee'], 'km'}
    calc['r_perigee'] = {R + oe['perigee'], 'km'}
    calc = pd.to_numeric(calc)

    # Calculate Eccentricity/Angular Momentum
    calc['eccentricity'] = {(calc['r_apogee']['VALUE'] - calc['r_perigee']['VALUE']) / (calc['r_apogee']['VALUE'] + calc['r_perigee']['VALUE']), '-'}
    calc['angular momentum'] = {sqrt(calc['r_perigee']['VALUE'] * mu * (1 + calc['eccentricity']['VALUE'])), 'km^2/s'}

    # Calculate semi-major/semi-minor axes
    calc['semi-major axis'] = (calc['r_apogee']['VALUE'] + calc['r_perigee']['VALUE']) / 2
    calc['semi-minor axis'] = calc['semi-major axis']['VALUE'] * sqrt(1 - calc['eccentricity']['VALUE'] ** 2)

    # Calculate Period of Orbit
    calc['period of orbit'] = (2 * pi / mu ** 2) * (calc['angular momentum']['VALUE'] / sqrt(1 - calc['eccentricity']['VALUE'] ** 2)) ** 3
    calc['period of orbit'] = calc['period of orbit']['VALUE'] / 60  # mins

    # Velocity at apogee/perigee
    calc['v_apogee'] = calc['angular momentum']['VALUE'] / calc['r_apogee']['VALUE']
    calc['v_perigee'] = calc['angular momentum']['VALUE'] / calc['r_perigee']['VALUE']

    # Display calculated values
    df = pd.DataFrame(calc, index=['VALUE'])
    df = df.transpose()
    # Append Units
    units.extend(['km', 'km', '-', 'km/s^2', 'km', 'km', 'min', 'km/s', 'km/s'])
    df['UNITS'] = units
    st.write('Calculated Values')
    st.write(df)
# def get_plt():


if __name__ == "__main__":
    main()
