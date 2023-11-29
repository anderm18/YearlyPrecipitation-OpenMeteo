# -*- coding: utf-8 -*-
"""Yearly Weather Statistics using OpenMeteo.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1IdgLXDvqfOw1YPKGiU5MkPqcEU5c3z5H

### Weather API
#### Yearly Precipitation Data Retrieval

This notebook uses the OpenMeteo Weather Archive API to retrieve past weather data for any given coordinates. It aims to provide an interface that will retrieve info on year to year weather data that aligns with the yearly measures from the International Tree Ring Datasets (https://www.ncei.noaa.gov/products/paleoclimatology/tree-ring) to measure the correlation between tree ring width and precipitation.

First, we need to install the OpenMeteo Python wrapper, under the hood this just uses the requests library, so we can setup a requests-cache and retry configurations such that the success rate of our querying class is more reliable and faster for multiple calls on the same years.
"""

# pip install openmeteo-requests

# pip install requests-cache retry-requests

import pandas as pd
import numpy as np
from typing import List, Tuple
import requests_cache
from retry_requests import retry
from datetime import datetime
import openmeteo_requests

"""This is the main part of the Notebook. The WeatherAPI class comes with one public method: `get_yearly_precipitation()`. It is documented as follows:

```
get_yearly_precipitation(year_start: int, year_end: int, longitude_latitude: Tuple, verbose=False)

Takes in parameters:

year_start: int -> Year to start measurement (inclusive)
year_end: int -> Year to end measurement (inclusive)
longitude_latitude: Tuple -> A 2 element tuple, whose first element is Longitude (int) and second is Latitude (int)
verbose (default False): bool -> Print debug info flag

The function uses the parameters to form a Pandas DataFrame that models precipitation overall sum, average, min, and max per year.
The Dataframe contains the following columns holding the above info:

year
precipitation_sum (in mm)
precipitation_daily_avg (in mm)
precipitation_min (in mm)
precipitation_max (in mm)

```

The class makes it so only one Request to the API is made, hopefully helping to speed up the Pipeline. Usually, the OpenMeteo API would only give you up to every day in a year, not info on the overall year, meaning you'd have to make multiple requests for each year. By only making 1 call we're significantly reducing the wait time due to network calls to the API. It does this by creating intervals over each year to process info for only a subset of the data that correlates to each year. Then, it just uses this calculated info to create a DataFrame and return it to the caller.
"""

class WeatherAPI:


	def __init__(self, expire_after=-1, retries=5, backoff_factor=.2):

		# Create Session with OpenMeteo, establish Endpoint
		self.cache = requests_cache.CachedSession('.cache', expire_after=expire_after)
		self.OpenMeteo = openmeteo_requests.Client(session=retry(self.cache, retries=retries, backoff_factor=backoff_factor))
		self.endpoint = "https://archive-api.open-meteo.com/v1/archive"


	def __process_dates(self, year_start: int, year_end: int) -> List[Tuple[int, int]]:

		f = "%m/%d/%Y"
		dates_list = [
			(int(datetime.strptime(f"01/01/{i}", f).timestamp()), int(datetime.strptime(f"12/31/{i}", f).timestamp())) for i in range(year_start, year_end+1)
		]

		return dates_list


	def __send_request(self, packet: dict, verbose=False) -> pd.DataFrame:

		reponse = None
		df = pd.DataFrame()
		start_year, end_year = packet['year_start'], packet['year_end']
		dates = self.__process_dates(start_year, end_year)
		packet['start_date'] = f"{packet['year_start']}-01-01"
		packet['end_date'] = f"{packet['year_end']}-12-31"

		if verbose:
			print(packet)

		try:
			response = self.OpenMeteo.weather_api(self.endpoint, params=packet)[0]
		except Exception as e:
			if verbose:
				print(e)
			return df

		if verbose:
			print(f"Coordinates {response.Latitude()}°E {response.Longitude()}°N")
			print(f"Elevation {response.Elevation()} m asl")
			print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
			print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

		daily = response.Daily()
		precip = daily.Variables(0).ValuesAsNumpy()

		last_ind = 0
		df_data = {
			"year": [],
			"precipitation_sum": [],
			"precipitation_daily_avg": [],
			"precipitation_min": [],
			"precipitation_max": []
		}

		for i in range(0, end_year-start_year+1):

			days = len(pd.date_range(
				start = pd.to_datetime(dates[i][0], unit = "s"),
				end = pd.to_datetime(dates[i][1], unit = "s"),
				freq = pd.Timedelta(seconds = 86400),
				inclusive = "left"
			))

			years_data = precip[last_ind:days+last_ind]
			df_data["year"].append(i+start_year)
			df_data["precipitation_sum"].append(years_data.sum())
			df_data["precipitation_daily_avg"].append(np.mean(years_data))
			df_data["precipitation_min"].append(np.min(years_data))
			df_data["precipitation_max"].append(np.max(years_data))

			last_ind=days+last_ind

		dataframe = pd.DataFrame(data=df_data)

		return dataframe


	def get_yearly_precipitation(self, year_start: int, year_end: int, long_lat: Tuple, verbose=False) -> pd.DataFrame:
		return self.__send_request({
			"latitude": long_lat[1],
			"longitude": long_lat[0],
			"year_start": year_start,
			"year_end": year_end,
			"daily": "precipitation_sum"
		}, verbose=verbose)

"""Now all we need is an instance of this class. You can modify the default values in the constructor to adjust settings about how the class interacts with the API:

expire_after: how long after the request is made to stop the waiting and return an expired request (default -1, or inifinite, to let OpenMeteo handle that)

retries: how many times to retry a failed request (default 5)

backoff_factor: adjust the backoff factor of the requests being sent out to OpenMeteo (default .2)

Let's test it on the years from 1970-2022 in Berlin:
"""

Weather = WeatherAPI()
df = Weather.get_yearly_precipitation(1970, 2022, (13.41, 52.52))

df

"""DataFrame looks good, now we can plot the data we have retrieved:"""

import matplotlib.pyplot as plt

plt.plot(df['year'], df['precipitation_sum'])
plt.xlabel('Year')
plt.ylabel('Sum of Precipitation')
plt.title('Total Precipitation per Year')
plt.show()

plt.plot(df['year'], df['precipitation_daily_avg'])
plt.xlabel('Year')
plt.ylabel('Average Precipitation')
plt.title('Average Precipitation per Year')
plt.show()