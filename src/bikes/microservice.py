from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import logging

# Import our weather service
from application import VERSION, HealthResponse, app_logging
from src.bikes.bikes import get_nearest_stations
from utils.utils import utc_time, run_service


SERVICE_NAME = "bike-microservice"
PORT = 8002

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
    version=VERSION
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
def root():
    """
    root endpoint returning service information
    """
    return {
        "service": SERVICE_NAME,
        "version": VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@bike_service.get("/health", response_model=HealthResponse)
def health_check():
    """
    checks the health of the service
    """
    health_check(
        service_name=SERVICE_NAME,
        logger=logger
    )


@bike_service.get("/get_address_nearest_stations", response_model=NearestStationsResponse)
def get_address_nearest_stations(
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
        port=PORT
    )


# Run the server
if __name__ == "__main__":
    # running the service
    run_bikes_service()
