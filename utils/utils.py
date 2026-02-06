from pythonjsonlogger.json import JsonFormatter
from singleton_decorator import singleton
from datetime import datetime, timezone
from functools import lru_cache
import numpy as np
import logging
import time

# typing imports
from typing import Dict, Tuple, Optional, Any
from pydantic import BaseModel
import numpy.typing as npt

# system libraries
from pathlib import Path
import httpx
import sys

# fast api related
from fastapi import FastAPI, Request
import uvicorn

# project configuration
from configuration import LOG_LEVEL, HOST

# log files path
LOGS = './src/logs/'

ENABLE_LOGS_PURGE = True

SERVICES_DEFAULT_LOG_LEVEL = 'info'


def distance(a: npt.ArrayLike, b: npt.ArrayLike, p: int = 2) -> float:
    """
    compute the L^p distance between two vectors a and b having the same dimension, p defaulted to 2 (Euclidean distance)
    """
    a = np.array(a)
    b = np.array(b)

    assert a.shape == b.shape

    return np.linalg.norm(a - b, ord=p)


def max_n(arr: npt.ArrayLike, n: int, descending: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """
    returns the n max values and their indices from the input array, in descending order by default
    """
    arr = np.array(arr)
    if n <= 0:
        return np.array([]), np.array([])

    # Get indices of the n max values
    indices = np.argpartition(a=arr, kth=-n)[-n:]

    # Sort these n values in descending order
    indices = indices[np.argsort(arr[indices])]

    if descending:
        indices = indices[::-1]

    values = arr[indices]

    return values, indices


def _offset_values(arr: npt.ArrayLike, v: float = np.inf, left: bool = True) -> np.ndarray:
    """
    offsetting values from an array, adding a default value at the beginning or end. The returned array has the same
      size as 'arr' so this is not an append operation (left or right) nor an extension
    """
    # both arr & out have the same shape
    arr = np.asarray(arr)
    out = np.empty_like(arr)

    if left:
        out[0] = v
        out[1:] = arr[:-1]

    else:
        out[-1] = v
        out[:-1] = arr[1:]

    return out


def utc_time(to_string: bool = False) -> datetime | str:
    """
    computes the zulu timestamp
    """
    # timezone.utc ensures the timestamp is expressed in Zulu +00:00 time
    zulu_time = datetime.now(timezone.utc)

    zulu_time = str(zulu_time) if to_string else zulu_time

    return zulu_time


@singleton
class AppLogging:
    def __init__(self, level: Optional[int] = logging.INFO):
        # logging level of the root logger
        self._level: int = level

        log_format, date_format = '%(name)s %(levelname)s %(asctime)s :%(message)s', '%Y-%m-%d %H:%M:%S'

        # default formatter for all console logs
        self._formatter: logging.Formatter = logging.Formatter(
            fmt=log_format,
            datefmt=date_format
        )

        # creates and stores the main logger
        self.root: Optional[logging.Logger] = None
        self._set_root_logger()

        # the following object won't store the root logger
        self.service_loggers: Dict[str, logging.Logger] = {}

        # this object is created once, that the bottom of this present file, avoiding circular imports later on
        logging.info('Root logger was setup successfully')

    def _set_root_logger(self) -> None:
        """
        sets up the root main logger of our application
        """
        root_logger = logging.getLogger()
        root_logger.setLevel(self._level)

        # clears existing handlers to reassign the ones we want
        root_logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(self._formatter)
        console_handler.setLevel(self._level)

        # 'root' logger is initialized at 'None' and replaced here
        self.root = root_logger

    def set_service_logger(
            self,
            service_name: str,
            level: Optional[int] = None,
            file_name: Optional[str] = None
    ) -> logging.Logger:
        """
        adds a logging configuration (logging handlers to the root logger) for a given microservice
        """
        # trying to initialize twice the same service logger (before the service is even running) represents a critical
        # error. ValueError is raised to prevent this behaviour
        if service_name in self.service_loggers:
            raise ValueError(f"Service logger {service_name} was already created")

        service_logger = logging.getLogger(name=service_name)

        # setting logger level using the default root logging level if no level was specified
        service_logger.setLevel(level if level is not None else self._level)

        log_format, date_format = '%(asctime)s: %(name)s: %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S'

        # using JSON formatter
        file_formatter = JsonFormatter(
            log_format,
            datefmt=date_format,
            rename_fields={"levelname": "level", "name": "logger"},
            static_fields={"service": service_name}
        )

        console_formatter = logging.Formatter(
            fmt=log_format,
            datefmt=date_format
        )

        # console handler: handling the printing of logs to the console
        console_handler = logging.StreamHandler(sys.stdout)

        # file handler: writes the logs in the specified file
        file_name = LOGS + file_name
        file_handler = logging.FileHandler(filename=file_name)

        # same formatter for both handlers
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)

        service_logger.addHandler(console_handler)
        service_logger.addHandler(file_handler)

        # storing the logger in the dictionary of root and service loggers
        self.service_loggers[service_name] = service_logger

        return service_logger

    def get_service_logger(self, service_name: str) -> Optional[logging.Logger]:
        """
        if defined, the service logger (named after the service) is returned
        """
        # not raising if the service does not appear in the service loggers object
        return self.service_loggers.get(service_name)


def purge_logs():
    """
    purging all the log files in the logs directory
    """
    logs_path = Path(LOGS)  # making the 'LOGS' variable into a path object

    if not logs_path.exists():  # Check if directory exists
        logging.error(f"Logs directory does not exist")
    else:
        i = 0

        for file in logs_path.iterdir():  # iterating on all files in the directory
            file.unlink()  # deleting file
            i += 1

        logging.info(f"Successfully purged {i} files from the logs directory")


class HealthResponse(BaseModel):
    """
    response object for the health check request
    """
    status: str
    timestamp: datetime
    service: str


class GatewayHealthResponse(BaseModel):
    """
    response object for the gateway health check request
    """
    # gateway attributes
    gateway_service: str
    gateway_status: int
    timestamp: str

    # services health attributes
    microservices_health: dict


def service_health_check(service_name: str, logger: Optional[logging.Logger]) -> Dict:
    """
    checks the health of a service
    """
    zulu_time = datetime.now(timezone.utc)

    logger = logger or logging
    logger.debug(f'Health check request received at {zulu_time} Zulu time')

    return {
        "status": "healthy",
        "timestamp": zulu_time,
        "service": service_name
    }


def run_service(service_name: str, service: FastAPI, port: int):
    """
    running a generic service
    """
    logging.info(f"Launching service {service_name}")

    if ENABLE_LOGS_PURGE:
        purge_logs()

    uvicorn.run(
        service,
        host=HOST,
        port=port,
        log_level=SERVICES_DEFAULT_LOG_LEVEL
    )


@lru_cache(maxsize=25)
def url(host: str, port: int, method: str):
    """
    constructs url to hit the api endpoint defined explicitly by the inputs
    """
    if method.startswith('/'):
        method = method[1:]

    return f"http://{host}:{port}/{method}"


async def send_request(
    *,
    request_url: str,
    method: str = "GET",
    timeout: float = 5.0,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=timeout) as client:
        # executing the request asynchronously using the async client object
        return await client.request(
            method=method,
            url=request_url,
            params=params,
            json=json,
            headers=headers,
        )


logger = logging.getLogger("timing middleware:")


def add_timing_middleware(app: FastAPI) -> None:
    """
    All requests to the specified app in argument pass by this middleware, timing their execution
    """
    @app.middleware("http")
    async def timing_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        logger.info(
            f"[{app.title}] {request.method} {request.url.path} took {duration:.4f}s"
        )

        return response


# setting up root logger once for the whole application: app scope
app_logging = AppLogging(level=LOG_LEVEL)
