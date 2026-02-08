import copy
from typing import Tuple, Dict, List
import numpy as np
import pandas as pd
import requests

from utils.utils import distance, max_n


# Station information and status endpoints
INFO_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_information.json"

STATUS_URL = "https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/station_status.json"

DROP_COLUMNS_STATION_INFO = (
    'rental_methods',
    'station_opening_hours',
    'numBikesAvailable',
    'numDocksAvailable',
    'is_installed',
    'is_returning',
    'last_reported'
)


def get_stations_info() -> Tuple[List[Dict], List[Dict]]:
    """
    Retrieves bike stations information and status from the respective endpoints
    """
    stations, status = (
        list(  # Converts to array
            requests.get(url).json()["data"]["stations"]  # requests, converts to json & does the appropriate lookup
        )
        for url in (INFO_URL, STATUS_URL)  # For both those URLs
    )

    return stations, status


def get_nearest_stations(
        location: Tuple[float, float],
        n: int = 3
):
    """
    Finding the n-nearest stations from a given location (lat, lon)
    """
    # the following function call is somewhat costly but implements lru_cache(max_size=1) so it will be costly only once
    stations_info, stations_status = get_stations_info()

    lat, lon = location

    distances = np.zeros(len(stations_info))

    for index, station in enumerate(stations_info):
        # Computing the distance from the (lat, lon) location
        distances[index] = distance((lat, lon), (station["lat"], station["lon"]))

    # Finding out the n-closest distances by passing "-distances" below
    _, indices = max_n(arr=-distances, n=n, descending=True)

    return [np.asarray(s)[indices] for s in (stations_info, stations_status)]


def format_stations_info(
        stations_info: List[np.array],
        stations_status: List[np.array]
) -> pd.DataFrame:
    """
    Synthesizes both objects in a single dataframe containing all the useful information
    """
    # We'll fill this list object with stations information
    data = []

    for station, status in zip(stations_info, stations_status):
        # If the following assertion does not pass, something went wrong
        assert station['station_id'] == status['station_id']

        # Unpacking info about the number
        mechanical, electrical = status.pop('num_bikes_available_types')
        station['mechanical'], station['electrical'] = mechanical['mechanical'], electrical['ebike']

        station.update(status)
        data.append(station)

    df = pd.DataFrame(data=data)

    # Removing useless columns
    for column in DROP_COLUMNS_STATION_INFO:
        df.drop(column, axis=1, inplace=True)

    return df


if __name__ == '__main__':
    station_info, station_status = get_nearest_stations(
        location=(48.852835, 2.385478)
    )

    info = format_stations_info(stations_info=station_info, stations_status=station_status)

    print(info)
