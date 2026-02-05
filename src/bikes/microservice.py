from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import logging

# Import our weather service
from utils.utils import utc_time, run_service, HealthResponse, app_logging, service_health_check
from src.bikes.bikes import get_nearest_stations

# project configuration
import configuration as conf


SERVICE_CONFIG = conf.SERVICES['microservices']['bikes']
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
    """
    pass


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
    service_health_check(
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
    # perform weather microservice call
    location = ...

    # stations_info, stations_status = get_nearest_stations(
    #     location=location
    # )

    # returning the formatted information
    # return format_stations_info(stations_info=station_info, stations_status=station_status)
    return {}


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
