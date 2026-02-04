from utils.errors import GeocodeConfidenceError, GeocodeInvalidResponse, GeocodeException
from typing import Dict
import pandas as pd
import numpy as np
import requests
import json


# government API endpoint to retrieve geolocation information from addresses
BAN_API_URL = "https://api-adresse.data.gouv.fr/search/"

# endpoint to request weather forecast
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# list of weather information fields we're interested in keeping
WEATHER_INFO = (
    'current_weather',
    'generationtime_ms',
    'timezone_abbreviation',
    'temperature_2m',
    'precipitation',
    'weather_code'
)

TIMEOUT = 5

# the service that identifies address and computes their latitude & longitude has a confidence score. we won't access
# its evaluation if the confidence score is below the following value
ADDRESS_SEARCH_CONFIDENCE_THRESHOLD = 0.9


def _geocode_address(address: str) -> Dict:
    """
    querying information from the address that will be passed to the weather requester
    """
    # performing the request
    r = requests.get(
        BAN_API_URL,
        params={
            "q": address,
            "limit": 1
            },
        timeout=TIMEOUT
    )

    # unpacking response attribute
    status, content = r.status_code, r.json()

    # using the following variable to raise an error for invalid response or not
    invalid_response = False

    if status != 200 or 'features' not in content:
        # if the request is not 'OK' or if the content has no 'features' key: raising
        invalid_response = True
    else:
        if 'features' in content:
            if not content['features']:
                # 'features' is empty, the response is invalid
                invalid_response = True
        else:
            # 'features' are not empty, everything is looking good
            pass

    if invalid_response:
        raise GeocodeInvalidResponse(
            message="Invalid open weather data API is invalid, check that the address is valid",
            status_code=status
        )

    feature = r.json()['features'][0]

    lon, lat = feature["geometry"]["coordinates"]

    confidence = np.around(feature['properties']['score'], 2)

    if confidence < ADDRESS_SEARCH_CONFIDENCE_THRESHOLD:
        raise GeocodeConfidenceError(
            message="Invalid address",  # using a message understandable by the API client
            details={"address": address},
            confidence_score=confidence,
            threshold=ADDRESS_SEARCH_CONFIDENCE_THRESHOLD
        )

    return {
        'latitude': lat,
        'longitude': lon,
        'confidence': confidence,
        'postcode': feature['properties']['postcode'],
        '_type': feature['properties']['_type']
    }


def _request_weather(params: dict) -> dict:
    """
    performs the weather data request given parameters
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
    formatting the weather data received from the service
    """
    # rounding the request runtime
    weather_data['public_weather_api_runtime_ms'] = np.around(weather_data.pop('generationtime_ms'), 4)

    # popping the dict value contained in 'current_weather' to add its items to our data dict
    weather_data.update(weather_data.pop('current_weather'))

    # converting the request timestamp to a Pandas timestamp
    weather_data['time'] = pd.Timestamp(weather_data['time'])

    # useless field
    weather_data.pop('interval')

    # renaming keys
    for old_key, new_key in {
        'timezone_abbreviation': 'timezone',
        'winddirection': 'wind_direction',
        'windspeed': 'wind_speed',
        'weathercode': 'weather_code'
    }.items():
        weather_data[new_key] = weather_data.pop(old_key)


def get_weather(address: str) -> dict:
    """
    querying the weather given an address in natural language
    """
    # retrieving the necessary information from the address
    address_info = _geocode_address(address=address)

    # the latitude and longitude are in the info, and will be used to request some data later on
    lat, lon = address_info['latitude'], address_info['longitude']

    # creating the payload mandatory to request the weather
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

    # requesting the weather data...
    response = _request_weather(params=params)

    # ... and extending the previously created dictionary with returned values
    weather_data.update(response)

    # presenting the data in the appropriate format
    _format_weather_data(weather_data=weather_data)

    return weather_data
