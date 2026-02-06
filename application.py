from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Dict
import multiprocessing
import logging

# utils functions
from utils.utils import (
    add_timing_middleware,
    GatewayHealthResponse,
    service_health_check,
    send_request,
    run_service,
    utc_time,
    url
)

# microservices imports
from src.bikes.microservice import NearestStationsResponse, run_bikes_service
from src.weather.microservice import WeatherResponse, run_weather_service

# project configuration
from configuration import (
    ENABLE_PROFILING,
    HEALTH_ENDPOINT,
    DOCS_ENDPOINT,
    HealthStatus,
    SERVICES,
    VERSION
)

LOG_LEVEL = logging.DEBUG

GATEWAY_CONFIG = SERVICES['gateway']
MICROSERVICES_CONFIG = SERVICES['microservices']

GATEWAY_NAME = GATEWAY_CONFIG['name']

# Creating FastAPI app object
gateway = FastAPI(
    title=GATEWAY_NAME,
    description="Backend dedicated to redirect weather related requests",
    version=VERSION
)

if ENABLE_PROFILING:
    add_timing_middleware(gateway)

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
        "version": VERSION,
        "status": "running",
        "docs": DOCS_ENDPOINT,
        "health": HEALTH_ENDPOINT
    }


@gateway.get(HEALTH_ENDPOINT, response_model=GatewayHealthResponse)
async def health_endpoint():
    """
    checks the health of the service
    """
    # will return the following object
    health = {
        'gateway_service': GATEWAY_NAME,
        'gateway_status': 200,
        'timestamp': None,
        'microservices_health': {}
    }

    # main gateway health check call
    gateway_health_response = service_health_check(
        service_name=GATEWAY_NAME,
        logger=None
    )

    health['timestamp'] = str(gateway_health_response['timestamp'])

    # object storing microservices health
    microservices_health = health['microservices_health']

    health_status = HealthStatus.STATUS_CODES.value  # ignore warning, the object has type HealthStatus, no dict

    # microservices calls
    for _, service_config in MICROSERVICES_CONFIG.items():
        # unpacking service name, port and timeout settings
        port, timeout, name = service_config['port'], service_config['timeout'], service_config['name']

        # building the correct url to request
        request_url = url(
            host='localhost',
            port=port,
            method=HEALTH_ENDPOINT
        )

        logging.info(f"Health-checking service: {name}")

        try:
            response = await send_request(
                request_url=request_url,
                timeout=timeout
            )

            service_status = health_status.get(response.status_code)

            value = (str(response.status_code), service_status)

        except (Exception, ) as e:
            logging.error(f"Health check request failed for service {name}: {e}")

            value = ('Unhealthy', str(e))

        # adding the microservice health status to the dictionary created above
        microservices_health[name] = value

        if value[0] != '200':
            # returning 'multi-status' if not all microservices are up and running
            health['gateway_status'] = 207

    return JSONResponse(
            status_code=health['gateway_status'],
            content=GatewayHealthResponse(**health).model_dump()
        )


class DashboardDataResponse(BaseModel):
    """
    response object for the dashboard data request
    """
    timestamp: str
    bikes_info: NearestStationsResponse
    weather_info: WeatherResponse


@gateway.get('/get_dashboard_data', response_model=DashboardDataResponse)
async def dashboard_data(
        address: str = Query(
            default='1 rue de Charonne, 75011',
            description="Computes dashboard data for the "
        )
):
    """
    checks the health of the service
    """
    timestamp = utc_time()

    logging.info(f"Received dashboard data request for address: {address}")

    # unpacking the two microservices configurations
    bikes_conf, weather_conf = (MICROSERVICES_CONFIG.get(k) for k in ('bikes', 'weather'))

    # executing both requests to get the nearest bike stations and the weather information
    try:
        bike_response = await send_request(
            request_url=
            url(
                host='localhost',  # host to request
                port=bikes_conf['port'],  # appropriate port taken from the configuration
                method='get_address_nearest_stations'  # appropriate method to query
            ),
            timeout=bikes_conf['timeout'],
            params={
                "address": address
            }
        )

        assert bike_response.status_code == 200, 'Request failed'

    except (Exception, ) as e:
        logging.error(f"An error occurred while requesting the nearest bike stations information: {e}")
        raise e

    try:
        weather_response = await send_request(
            request_url=
            url(
                host='localhost',
                port=weather_conf['port'],
                method='get_weather_info'
            ),
            timeout=weather_conf['timeout'],
            params={
                "address": address
            }
        )

        assert weather_response.status_code == 200, 'Request failed'

    except (Exception, ) as e:
        logging.error(f"An error occurred while requesting the weather information: {e}")
        raise e

    return {
        'timestamp': str(timestamp),
        "bikes_info": NearestStationsResponse(**bike_response.json()),
        "weather_info": WeatherResponse(**weather_response.json()),
    }


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
