import pandas as pd
import streamlit as st
from math import pi, sqrt
from collections import defaultdict


# # Michael Levy 9/7/2020


# Set config/title
st.beta_set_page_config(page_title='ORBIT PLAYGROUND', page_icon="🚀", layout='centered', initial_sidebar_state='collapsed')
st.title('Orbit Playground')
'''
Link to [GitHub Repo](https://github.com/levymp/orbit_visual) where this is being developed.\n

**Here are the equations I used for these calculations:**\n
**Radius of Apogee/Perigee:**\n
$$\\boxed{r_{a/p} = R_{E} + r_{a/p}}$$\n
**Eccentricity:**\n
$$\\boxed{e = \\frac{(r_{a} - r_{p})}{(r_{a} +r_{p})}}$$\n

**Semi-Major Axis:**\n
$$\\boxed{a = \\frac{(r_{a} + r_{p})}{2}}$$\n

**Semi-Minor Axis:**\n
$$\\boxed{b = a\\sqrt{1 - e^2}}$$\n

**Angular Momentum:**\n
$$\\boxed{h^2 = r_{p}\mu(1 + e)}$$\n

**Period of Orbit (seconds):**\n
$$\\boxed{T = \\frac{2\pi}{\\sqrt{\mu}}a^{3/2}}$$\n

**Velocity at Apogee/Perigee:**\n
$$\\boxed{v_{a/p} = \\frac{r_{a/p}}{h}}$$

'''
# Initial Given Values
'**Input Values:**'

# Get User Input
apogee = st.number_input('Apogee (km)', value=3500)
perigee = st.number_input('Perigee (km)', value=480)
inclination = st.number_input('Inclination (deg)', value=90)
argument_of_perigee = st.number_input('Argument of Perigee (deg):', value=270)
RAAN = st.number_input('Right Ascension of the Ascending Node (deg):', value=180)

# Dictionary of Values -> Pandas DataFrame
oe = {'apogee': apogee, 'perigee': perigee, 'inclination': inclination, 'argument of perigee': argument_of_perigee, 'Right Ascension of the Ascending Node': RAAN}
given = pd.DataFrame(oe, index=['VALUE']).transpose()

# Append Units
units = ['km', 'km', 'deg', 'deg', 'deg']
given['UNITS'] = units

# Display values
'**Given Values**'
st.write(given)

# Show known constants
'**Known Constants**'
known = pd.DataFrame({'Radius of Earth': 6378, 'Gravitational Parameter': 398600}, index=['VALUE']).transpose()

# Append Units
known['UNITS'] = ['km', 'km^3/s^2']

# Display Values
st.write(known)

# Set local variables
# Radius of Earth
R = known['VALUE']['Radius of Earth']  # km

# Gravitational Parameter
mu = known['VALUE']['Gravitational Parameter']  # km^3/s^2

def main():
    # New dataframe for calculated values assign -> {value, units}
    calc = defaultdict(list)

    # Assign radius of apogee and perigee
    calc['r_apogee'] = R + oe['apogee']
    calc['r_perigee'] = R + oe['perigee']
    
    # Calculate Eccentricity/Angular Momentum
    calc['eccentricity'] = (calc['r_apogee'] - calc['r_perigee']) / (calc['r_apogee'] + calc['r_perigee'])
    if calc['eccentricity'] > 1:
        st.warning('Eccentricity is > 1 these equations do not calculate orbits correctly')
    calc['angular momentum'] = sqrt(calc['r_perigee'] * mu * (1 + calc['eccentricity']))

    # Calculate semi-major/semi-minor axes
    calc['semi-major axis'] = (calc['r_apogee'] + calc['r_perigee']) / 2
    calc['semi-minor axis'] = calc['semi-major axis'] * sqrt(1 - calc['eccentricity'] ** 2)

    # Calculate Period of Orbit
    calc['period of orbit'] = (2 * pi / mu ** 2) * (calc['angular momentum'] / sqrt(1 - calc['eccentricity'] ** 2)) ** 3
    calc['period of orbit'] = calc['period of orbit'] / 60  # mins

    # Velocity at apogee/perigee
    calc['v_apogee'] = calc['angular momentum'] / calc['r_apogee']
    calc['v_perigee'] = calc['angular momentum'] / calc['r_perigee']

    # Display calculated values
    df = pd.DataFrame(calc, index=['VALUE'])
    df = df.transpose()
    df = df.round(2)

    # Append Units
    units = ['km', 'km', '-', 'km^2/s', 'km', 'km', 'min', 'km/s', 'km/s']
    df['UNITS'] = units

    '**Calculated Values**'
    st.write(df)

    '**ORBIT VISUAL COMING SOON!**'


if __name__ == "__main__":
    main()
