"""
FastAPI Weather Microservice
Provides REST API endpoints for weather information
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Tuple, Dict
from datetime import datetime
import logging

# Import our weather service
from utils.utils import AppLogging, utc_time, purge_logs, ENABLE_LOGS_PURGE, health_check, run_service
from src.weather.weather import get_weather
from utils.errors import GeocodeException


SERVICE_NAME = "weather-microservice"
VERSION = "1.0.0"
PORT = 8001

LOG_LEVEL = logging.DEBUG

# setting up root logger: app scope
app_logging = AppLogging(level=logging.INFO)

# setting up service logger: service scope
logger = app_logging.set_service_logger(
    service_name=SERVICE_NAME,
    level=logging.DEBUG,
    file_name=f'{SERVICE_NAME}:{utc_time()}.log'
)

# Creating FastAPI app object
weather_service = FastAPI(
    title=SERVICE_NAME,
    description="Backend dedicated to redirect weather related requests",
    version=VERSION
)

# Add CORS middleware for frontend integration
weather_service.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    """
    response object for the health check request
    """
    status: str
    timestamp: datetime
    service: str


class WeatherResponse(BaseModel):
    """
    response object for the weather data request
    """
    coordinates: Tuple[float, float]
    address: str = ''
    public_weather_api_runtime_ms: float
    time: datetime
    temperature: float
    is_day: int
    timezone: str = ''
    wind_direction: int
    wind_speed: float
    weather_code: int


@weather_service.get("/", response_model=Dict[str, str])
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


@weather_service.get("/health", response_model=HealthResponse)
def health_check():
    """
    checks the health of the service
    """
    health_check(
        service_name=SERVICE_NAME,
        logger=logger
    )


@weather_service.get("/get_weather_info", response_model=WeatherResponse)
def get_weather_info(
        address: str = Query(default='1 rue de Charonne, 75011', description="What's the weather like at this address?")
):
    """
    requests weather information
    """
    try:
        weather_data = get_weather(address)

        logging.info(f"Requested weather information for address {address}: {weather_data}")
        return weather_data

    except GeocodeException as e:
        logger.error(f"An exception occurred while retrieving the geocode of the address: {address}")
        raise HTTPException(status_code=e.status_code, detail=str(e))

    except Exception as e:
        logging.error(f"An exception occurred while retrieving the weather info: {e}")
        raise HTTPException(status_code=500, detail=f"Could not retrieve weather data: {str(e)}")


if __name__ == "__main__":
    # running the service
    run_service(
        service_name=SERVICE_NAME,
        service=weather_service,
        port=PORT
    )
