from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from typing import Dict
import multiprocessing
import logging

# utils functions
from utils.utils import (
    service_health_check,
    HealthResponse,
    app_logging,
    run_service,
    utc_time,
    url
)

# microservices imports
from src.weather.microservice import run_weather_service
from src.bikes.microservice import run_bikes_service

# project configuration
import configuration as conf

LOG_LEVEL = logging.DEBUG

GATEWAY_CONFIG = conf.SERVICES['gateway']
GATEWAY_NAME = GATEWAY_CONFIG['name']


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
    version=conf.VERSION
)

# Add CORS middleware for frontend integration
gateway.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@gateway.get("/", response_model=Dict[str, str])
async def root():
    """
    root endpoint returning service information
    """
    return {
        "service": GATEWAY_NAME,
        "version": conf.VERSION,
        "status": "running",
        "docs": conf.DOCS_ENDPOINT,
        "health": conf.HEALTH_ENDPOINT
    }


@gateway.get(conf.HEALTH_ENDPOINT, response_model=HealthResponse)
async def health_endpoint():
    """
    checks the health of the service
    """
    # main gateway health check call
    service_health_check(
        service_name=GATEWAY_NAME,
        logger=logger
    )

    # microservices calls
    for _, service_config in conf.SERVICES['microservices'].items():
        host = service_config['host'] or conf.HOST
        port = service_config['port']
        endpoint = conf.HEALTH_ENDPOINT

        service_url = url(
            host=host,
            port=port,
            method=endpoint
        )

        try:
            response = requests.get(f"{microservice_url}/health", timeout=0)
            microservices_health[microservice_name] = response.json()
        except Exception as e:
            logger.error(f"Health check failed for {microservice_name}: {str(e)}")
            microservices_health[microservice_name] = {
                "status": "unreachable",
                "error": str(e)
            }

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        service=GATEWAY_NAME
    )


def run_gateway():
    run_service(
        service_name=GATEWAY_NAME,
        service=gateway,
        port=GATEWAY_CONFIG['port']
    )


def run_application():
    """
    running the gateway & microservices
    """
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
