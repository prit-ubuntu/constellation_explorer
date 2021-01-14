from skyfield.api import load, wgs84
import pandas as pd
import numpy as np
import pytz

# SETUP LIST OF ALL CONSTELLATIONS
# http://systemarchitect.mit.edu/docs/delportillo18b.pdf 
_MINELEVATIONS = {'PLANET': 80, 'SPIRE': 80, 'STARLINK': 80, 'SWARM': 80, 'ONEWEB': 80, 'GALILEO': 87, 'BEIDOU': 87} 
# Names of all constellations
CONSTELLATIONS = sorted(list(_MINELEVATIONS.keys()))
_URL = 'http://celestrak.com/NORAD/elements/'


class SatConstellation(object):
    '''
    Object that contains all relevant information and methods for constellation!
    '''
    def __init__(self, constellation, debug=False):
        self.constellation = constellation
        self._debug = debug
        self.initalized = False
        # Download Satellite Data
        self._importSats()

    def getSchedule(self):
        '''
        @brief  return schedule of passes (if created). Only return simplified schedule.

        @return Schedule'''
        try:
            return self.passes[['RISE TIME', 'CULMINATE TIME', 'SET TIME']].copy()
        except AttributeError:
            return False

    def _importSats(self):
        '''
        @brief Take in constellation name and get all relevant information

        @return writes sat object to
        '''

        # check that desired constellation is valid
        if self.constellation.upper() not in CONSTELLATIONS:
            return

        url = f'{_URL}{self.constellation.lower()}.txt'

        try:
            self.satellites = load.tle_file(url)
            self.count = len(self.satellites)
            self.initalized = True
        except Exception as e:
            print('COULD NOT FIND CONSTELLATION:', e)

    def generatePasses(self, position, dateRange, timezone):
        '''!
        @brief  Generate the passes of a specific constellation over a specified location and time range.

        @param position    TUPLE of latitude and longitude        
        @param dateRange    TUPLE of start/stop datetime objects (with timezone)
        @param timezone     STRING of desired timezone

        @return passes      generate passes vector
        '''
        # check if initialized
        if not self.initalized:
            return False

        ts = load.timescale()
        self.cityLatLon = wgs84.latlon(position[0], position[1])

        self.time = (ts.from_datetime(dateRange[0]), ts.from_datetime(dateRange[1]))
        self.tz = pytz.timezone(timezone)
        self._checkPasses()

    def _checkPasses(self):
        '''
        @brief find all passes for each satellite in the specified constellation over the lat/lon.

        @return list of satellite name with rise/culmination/setting time
        '''

        num_passes = np.zeros(self.count)
        time_list, name_list = [], []

        for id, sat in enumerate(self.satellites):
            times, events = sat.find_events(self.cityLatLon,
                                            self.time[0],
                                            self.time[1],
                                            _MINELEVATIONS[self.constellation])

            # check if any passes have occured for a specific satellite
            if len(events):
                # find the number of passes
                num_passes[id] = np.count_nonzero(np.where(events==0))

                rise_events, culmination_events, setting_events = times[np.where(events==0)], times[np.where(events==1)], times[np.where(events==2)]

                for i in range(len(rise_events)):
                    try:
                        time_list.append([rise_events[i], culmination_events[i], setting_events[i]])
                        name_list.append(sat.name)
                    except Exception:
                        if self._debug:
                            print(len(rise_events), len(culmination_events), len(setting_events))
                        else:
                            pass

                if self._debug:
                    for ti, event in zip(times, events):
                        print('Satellite Name:', sat.name)
                        name = ('rise above min elevation', 'culminate', 'set below min elevation')[event]
                        print(ti.utc_strftime('%Y %b %d %H:%M:%S'), name)

        self.schedule_list = list(zip(time_list, name_list))
        self.num_passes = num_passes

    def generateHistogram(self):
        # TODO: GENERATE HISTOGRAM FUNCTION
        # st.write(sat_times[['SAT NAME', 'TIME']])
        # st.write(sat_times["DATETIME"].dt.day)
        # values = sat_times.groupby([sat_times["DATETIME"].dt.day, sat_times["DATETIME"].dt.hour]).count()
        # df2 = values[['SAT NAME']]
        pass

    def generateSchedule(self):
        '''
        @return passes      PANDAS df [Satellite Name, Time of Rise (string), Culminate (string), Set (string)(Datetime object)]
        '''

        comparison_list, arranged_list = [], []
        sl = self.schedule_list

        # Compare events and obtain indices in ascending order
        for event_occur in sl: comparison_list.append(event_occur[0][0].toordinal())
        
        arrange_index = np.argsort(np.array(comparison_list))

        # Append new list with events from most recent to farthest
        # three as strings and three as date time objects
        for index in arrange_index:
            arranged_list.append([sl[index][1], \
                                sl[index][0][0].utc_datetime().astimezone(self.tz).strftime('%Y %b %d %H:%M:%S'), \
                                sl[index][0][1].utc_datetime().astimezone(self.tz).strftime('%Y %b %d %H:%M:%S'), \
                                sl[index][0][2].utc_datetime().astimezone(self.tz).strftime('%Y %b %d %H:%M:%S'),
                                sl[index][0][0].utc_datetime(), sl[index][0][1].utc_datetime(), sl[index][0][2].utc_datetime()])

        self.passes = pd.DataFrame(np.array(arranged_list), columns=['ASSET', 'RISE TIME', 'CULMINATE TIME', 'SET TIME', 'R', 'C', 'S'])
        self.passes.set_index('ASSET', inplace=True)

    