from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from fastapi import FastAPI
from typing import Dict
import multiprocessing
import logging

# Import our weather service
from utils.utils import AppLogging, utc_time, health_check, run_service


GATEWAY_NAME = "application-gateway"
VERSION = "1.0.0"

HOST = '0.0.0.0'
PORT = 8000

LOG_LEVEL = logging.DEBUG

# setting up root logger: app scope
app_logging = AppLogging(level=LOG_LEVEL)

# setting up service logger: service scope
logger = app_logging.set_service_logger(
    service_name=GATEWAY_NAME,
    level=logging.DEBUG,
    file_name=f'{GATEWAY_NAME}:{utc_time()}.log'
)

# Creating FastAPI app object
gateway = FastAPI(
    title=GATEWAY_NAME,
    description="Backend dedicated to redirect weather related requests",
    version=VERSION
)

# Add CORS middleware for frontend integration
gateway.add_middleware(
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


@gateway.get("/", response_model=Dict[str, str])
def root():
    """
    root endpoint returning service information
    """
    return {
        "service": GATEWAY_NAME,
        "version": VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@gateway.get("/health", response_model=HealthResponse)
def health_check():
    """
    checks the health of the service
    """
    health_check(
        service_name=GATEWAY_NAME,
        logger=logger
    )


def run_gateway():
    run_service(
        service_name=GATEWAY_NAME,
        service=gateway,
        port=PORT
    )


def run_application():
    """
    running the gateway & microservices
    """
    # importing microservices at runtime to avoid circular imports
    from src.weather.microservice import run_weather_service
    from src.bikes.microservice import run_bikes_service

    processes = []

    try:
        processes.extend(
            [
                multiprocessing.Process(target=run_weather_service),  # process dedicated to run the weather service
                multiprocessing.Process(target=run_bikes_service),  # ... bikes service
                multiprocessing.Process(target=run_gateway)  # and finally, running the gateway
            ]
        )

        for p in processes:
            p.start()

        for p in processes:
            p.join()

    except (Exception, ) as e:
        logging.critical(f'An error occurred, forcing the application to stop {e}')

        logging.info(f'Killing the processes')
        for process in processes:
            process.terminate()

        # Wait for processes to terminate
        for process in processes:
            process.join(timeout=5)

        logging.info('Killed microservices & gateway')

        raise e


if __name__ == "__main__":
    # running the service
    run_application()
