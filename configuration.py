"""
project constants & configurations
"""

from enum import Enum


# application version
VERSION = "1.0.0"

# global host used by all services
HOST = '0.0.0.0'

# global logging level used by all services for now, might specify later on
LOG_LEVEL = 'INFO'

# global timeout
TIMEOUT = 5

# allowing profiling in the applications
ENABLE_PROFILING = True

# TODO: transform this object to an Enum object
SERVICES = {
    'gateway': {
        'name': 'application-gateway',
        'host': HOST,
        'port': 8000,
        'log': LOG_LEVEL
    },
    # same host for all microservices for now
    'microservices': {
        'weather': {
            'name': 'weather-microservice',
            'host': None,
            'port': 8001,
            'log': LOG_LEVEL,
            'timeout': TIMEOUT
        },
        'bikes': {
            'name': 'bikes-microservice',
            'host': None,
            'port': 8002,
            'log': LOG_LEVEL,
            'timeout': TIMEOUT
        }
    }
}

HEALTH_ENDPOINT = '/health'

DOCS_ENDPOINT = '/docs'


class HealthStatus(Enum):
    HEALTHY: str = 'healthy'
    UNREACHABLE: str = 'unreachable'
    DOWN: str = 'down'
    TIMEOUT: str = 'timeout'
    BAD_REQUEST: str = 'bad request'
    INTERNAL_ERROR: str = 'internal error'

    STATUS_CODES: dict = {
        200: 'healthy',
        400: 'bad request',
        408: 'timeout',
        500: 'internal error',
        520: 'down'
    }
