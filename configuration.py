"""
project constants & configurations
"""

# application version
VERSION = "1.0.0"

# global host used by all services
HOST = '0.0.0.0'

# global logging level used by all services for now, might specify later on
LOG_LEVEL = 'INFO'

# global timeout
TIMEOUT = 5

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
