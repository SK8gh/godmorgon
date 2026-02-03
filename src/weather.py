import pandas as pd
import numpy as np
import requests


# Government API endpoint to retrieve geolocation information from addresses
BAN_API_URL = "https://api-adresse.data.gouv.fr/search/"

# Endpoint to request weather forecast
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# List of weather information fields we're interested in keeping
WEATHER_INFO = ('current_weather', 'generationtime_ms', 'timezone_abbreviation', )

TIMEOUT = 5


def _geocode_address(address: str):
    """
    Querying information from the address that will be passed to the weather requester
    """
    # Performing the request
    r = requests.get(
        BAN_API_URL,
        params={
            "q": address,
            "limit": 1
        },
        timeout=TIMEOUT
    )

    # Will raise if exceptions were caught
    r.raise_for_status()

    feature = r.json()['features'][0]

    lon, lat = feature["geometry"]["coordinates"]

    return {
        'latitude': lat,
        'longitude': lon,
        'confidence': np.around(feature['properties']['score'], 2),
        'postcode': feature['properties']['postcode'],
        '_type': feature['properties']['_type']
    }


def _request_weather(params: dict) -> dict:
    """
    Performs the weather data request given parameters
    """
    r = requests.get(
        WEATHER_URL,
        params=params,
        timeout=TIMEOUT
    )

    weather_data = {k: v for k, v in r.json().items() if k in WEATHER_INFO}

    return weather_data


def _format_weather_data(weather_data: dict) -> None:
    """
    Formatting the weather data received from the service
    """
    # Rounding the request runtime
    weather_data['generationtime_ms'] = np.around(weather_data['generationtime_ms'], 4)

    # Popping the dict value contained in 'current_weather' to add its items to our data dict
    weather_data.update(weather_data.pop('current_weather'))

    # Converting the request timestamp to a Pandas timestamp
    weather_data['time'] = pd.Timestamp(weather_data['time'])

    # Useless field
    weather_data.pop('interval')


def get_weather(address: str) -> dict:
    """
    Querying the weather given an address in natural language
    """
    # Retrieving the necessary information from the address
    address_info = _geocode_address(address=address)

    # The latitude and longitude are in the info, and will be used to request some data later on
    lat, lon = address_info['latitude'], address_info['longitude']

    # Creating the payload mandatory to request the weather
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,  # Real-time weather
        "timezone": "Europe/Paris"  # Making the hypothesis that
    }

    weather_data = {
        'coordinates': (lat, lon),
        'address': address
    }

    # Requesting the weather data...
    response = _request_weather(params=params)

    # ... and extending the previously created dictionary with returned values
    weather_data.update(response)

    # Presenting the data in the appropriate format
    _format_weather_data(weather_data=weather_data)

    return weather_data
