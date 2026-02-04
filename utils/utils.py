from pythonjsonlogger.json import JsonFormatter
from typing import Dict, Tuple, Optional
from datetime import datetime, timezone
from fastapi import FastAPI
import numpy.typing as npt
from pathlib import Path
import numpy as np
import logging
import uvicorn
import sys

from api import HOST  # importing the value of the server hosting the services


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


def utc_time() -> datetime:
    """
    computes the zulu timestamp
    """
    # timezone.utc ensures the timestamp is expressed in Zulu +00:00 time
    return datetime.now(timezone.utc)


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


def health_check(service_name: str, logger: logging.Logger) -> Dict:
    """
    checks the health of a service
    """
    zulu_time = datetime.now(timezone.utc)

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
