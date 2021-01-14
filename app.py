from datetime import (datetime as dt, time, timedelta)
from pytz import timezone, all_timezones
from collections import defaultdict
import plotly.figure_factory as ff
import constellation_utils as cu
import matplotlib.pyplot as plt
from tzwhere import tzwhere
from math import pi, sqrt
import streamlit as st
import pandas as pd


# @Author: Michael Levy and Prit Chovatiya 

# Set config/title
st.set_page_config(page_title='ORBITS', page_icon="🚀", layout='centered', initial_sidebar_state='expanded')
st.title('LOCAL CONSTELLATION TRACKER')

about = ''' Welcome to the satellite constellation tracker tool. 
With thousands of satellites passing over the skies, 
we wanted to create a tool for you to identify different satellites 
from various active constellations. Our tool provides you the name, 
date and time of all satellites in a particular constellation visible 
from 50 degrees above the horizon. 
   
   To get started, enter latitude and longitude of your location, date range & constellation 
of your choice in the side bar on the left. 

   Happy satellite gazing!!! 🛰 🌌 🚀
'''

st.sidebar.write('## SELECT PAGE')
page_res = st.sidebar.selectbox('', ('CONSTELLATION TRACKER', 'ORBIT PLAYGROUND'))

if page_res == 'CONSTELLATION TRACKER':
        
    locations = {'SAN FRANCISCO': (37.78, -122.41),
                'NEW YORK': (40.71, -74.0),
                'MUMBAI': (19.08, 72.88),
                'LONDON': (51.5, -0.13),
                'SHANGHAI': (31.23, 121.47),
                'CAPE TOWN': (-33.92, 18.42),
                'RIO DE JIANERIO': (-22.91, -43.1),
                'SYDNEY': (-33.87, 151.21),
                'MOSCOW': (55.76, 37.62),
                'TOKYO': (35.68, 139.65),
                'REYKJAVIK': (64.15, 21.94),
                'CAIRO': (30.04, 31.24),
                'SANTIAGO': (-33.45, -70.67),
                'MEXICO CITY': (19.43, -99.13),
                'ATHENS': (37.98, 23.73),
                'PARIS': (48.86, 2.35),
                'ROME': (41.90, 12.50), 
                'CORVALLIS (GO BEAVS!)': (44.56, -123.26), 
                'PORTLAND': (45.51, -122.68), 
                'SANTA CRUZ': (36.97, -122.03), 
                'WEST LAFAYETTE (GO BOILERS!)': (40.43, -86.91), 
                'ANN ARBOR (GO BLUE!)': (42.28, -83.74), 
                'RAJKOT': (22.30, 70.80)
                }
    st.sidebar.write('#### EXAMPLES')
    # get list of locs
    locs = sorted(locations.keys())
    # indx
    indx = locs.index('ANN ARBOR (GO BLUE!)')
    
    example = st.sidebar.selectbox('', options=locs, index=indx,key='1123sdf')
    c1, c2 = st.beta_columns(2)
    with c1:
        st.write('#### **INPUT LATITUDE**')
        lat = st.number_input('', min_value= -90., max_value= 90., value=locations[example][0], key='lsdksdfjf')
    with c2:
        st.write('#### **INPUT LONGITUDE**')
        lon = st.number_input('', min_value= -180., max_value=180., value=locations[example][1], key='lskdjf')
    position = (lat, lon)
    if lat > 0:
        dir1 = 'N'
    else:
        dir1 = 'S'
    if lon > 0:
        dir2 = 'E'
    else:
        dir2 = 'W'

    # display location
    st.map(data=pd.DataFrame({'lat': lat, 'lon': lon}, index=[0]), zoom=5, use_container_width=False)

    # display desired location
    # st.sidebar.write('### DESIRED LOCATION:')

    # st.sidebar.write(f'### {page_res}')


    st.sidebar.write('#### PICK A CONSTELLATION')
    constellationChoice = st.sidebar.selectbox('', options=cu.CONSTELLATIONS, index=len(cu.CONSTELLATIONS)-1, key='lskdjf')
    if constellationChoice == 'STARLINK':
        st.sidebar.warning('STARLINK HAS LOTS OF SATELLITES CONSIDER SHORTENING TIMEFRAME')
    # constellationChoice = constellationChoice.lower()
    # st.sidebar.write(f'#### **DESIRED LOCATION:**\n {abs(round(lat, 2))} {dir1}, {abs(round(lon, 2))} {dir2}')
    
    # @st.cache(suppress_st_warning=True)
    def gettimezone(position):
        '''Return string of local timezone'''
        tz = tzwhere.tzwhere()
        return tz.tzNameAt(position[0], position[1])

    # get timezone string
    # st.sidebar.write('#### **TIMEZONE**')

    zone = gettimezone(position)
    
    if isinstance(zone, str):
        newZone = st.sidebar.checkbox('DIFFERENT TIMEZONE?', value=False, key='lskdjfln2')
    else:
        '### SELECT TIMEZONE BELOW!'
        # newZone = st.sidebar.checkbox('SELECT TIMEZONE BELOW!', value=True, key='lskdjfln2')
        newZone = True


    # give option to select a different timezone
    if newZone:
        zone = st.sidebar.selectbox('SELECT DESIRED TIMEZONE', all_timezones, index=586, key='lskdjflksdjf')
        
    # st.sidebar.write('### **CURRENT TIMEZONE**')
    st.sidebar.code('TIMEZONE: ' + zone.replace('/', ', ').replace('_', ' '), 'python')
  
    st.sidebar.write('### DATE RANGE')
    tz = timezone(zone)
    # get current date in timezone
    currentDate = dt.now(tz)
    # currentDate = currentDate.replace(tzinfo=tz)
    timeFrame = st.sidebar.date_input('', (currentDate, currentDate + timedelta(days=3)), key='alksdjflk')

    # set start and end time
    # check if the start day is current date 
    if timeFrame[0].day == currentDate.date().day:
        # use the current time
        tstart = currentDate.time().replace(tzinfo=tz)
    else:
        # use the start of the day
        tstart = time(0, 0, 0, 0, tz)
    # assign end date
    tend = time(23, 59, 59, 0, tz)

    # make sure the dateRange is a tuple depending on user selection
    if isinstance(timeFrame, tuple):
        # user gave a range of dates
        try:
            dateRange = (dt.combine(timeFrame[0], tstart), dt.combine(timeFrame[1], tend))
        except IndexError:
            dateRange = (dt.combine(timeFrame[0], tstart), dt.combine(timeFrame[0], tend))
    else:
        # user gave one date (need to do start -> end)
        dateRange = (dt.combine(timeFrame, tstart), dt.combine(timeFrame, tend))

    # st.stop()
    # create constellation
    @st.cache(suppress_st_warning=True)
    def getConstellation(constellationChoice, position, dateRange, zone):
        constellation = cu.SatConstellation(constellationChoice)
        # get passes
        constellation.generatePasses(position, dateRange, zone)
        # create schedule
        constellation.generateSchedule()
        return constellation.getSchedule()

    # get constellation object
    df = getConstellation(constellationChoice, position, dateRange, zone)

    # display schedule
    '### SCHEDULE OF SATELLITE PASSES'
    st.write(df)

    # TODO: Add histogram and other relevant data

    # STOP APP FROM CONTINUING
    st.stop()


################################################################################################################
############################ LEGACY APP ########################################################################
################################################################################################################
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
