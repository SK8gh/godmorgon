from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Dict
import logging

# Import objects from our project
from utils.utils import (
    add_timing_middleware,
    service_health_check,
    HealthResponse,
    run_service,
    app_logging,
    utc_time
)

from src.bikes.bikes import get_nearest_stations, format_stations_info
from src.weather.weather import geocode_address

# project configuration
import configuration as conf


SERVICE_CONFIG, WEATHER_SERVICE = (conf.SERVICES['microservices'].get(k) for k in ('bikes', 'weather'))
SERVICE_NAME = SERVICE_CONFIG['name']

# setting up service logger: service scope
logger = app_logging.set_service_logger(
    service_name=SERVICE_NAME,
    level=logging.DEBUG,
    file_name=f'{SERVICE_NAME}:{utc_time()}.log'
)

# Creating FastAPI app object
bike_service = FastAPI(
    title=SERVICE_NAME,
    description="Backend dedicated to redirect weather related requests",
    version=conf.VERSION
)

if conf.ENABLE_PROFILING:
    add_timing_middleware(bike_service)

# Add CORS middleware for frontend integration
bike_service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NearestStationsResponse(BaseModel):
    """
    response object containing info about the nearest stations from an address. computed from df.to_dict method call
    """
    nearest_stations: dict


@bike_service.get("/", response_model=Dict[str, str])
async def root():
    """
    root endpoint returning service information
    """
    return {
        "service": SERVICE_NAME,
        "version": conf.VERSION,
        "status": 'running',
        "docs": conf.DOCS_ENDPOINT,
        "health": conf.HEALTH_ENDPOINT
    }


@bike_service.get(conf.HEALTH_ENDPOINT, response_model=HealthResponse)
async def health_endpoint():
    """
    checks the health of the service
    """
    return service_health_check(
        service_name=SERVICE_NAME,
        logger=logger
    )


@bike_service.get("/get_address_nearest_stations", response_model=NearestStationsResponse)
async def get_address_nearest_stations(
        address: str = Query(
            default='1 rue de Charonne, 75011',
            description="What are the nearest bike stations to this address?"
        )
):
    """
    retrieving the nearest bike stations to the address passed as argument
    """
    # perform function call to get the location (latitude, longitude) from the address passed as argument
    location = geocode_address(address=address)

    stations_info, stations_status = get_nearest_stations(
         location=(location['latitude'], location['longitude'])  # tuple arg containing (lat, lon)
    )

    # returning the formatted information
    response = format_stations_info(stations_info=stations_info, stations_status=stations_status)

    return {'nearest_stations': response.to_dict()}


def run_bikes_service():
    run_service(
        service_name=SERVICE_NAME,
        service=bike_service,
        port=SERVICE_CONFIG['port']
    )


# Run the server
if __name__ == "__main__":
    # running the service
    run_bikes_service()
