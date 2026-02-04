from typing import Optional, Dict, Any


class CustomException(Exception):
    """
    base exception for all custom exceptions
    """
    def __init__(
            self,
            message: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None
    ):
        self.details = details or {}
        super().__init__(message)  # does not accept kwargs


class WeatherServiceException(CustomException):
    """
    exception raised for errors in the weather service
    """
    def __init__(
            self,
            status_code: int,
            message: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code

        super().__init__(message=message, details=details)


class GeocodeException(WeatherServiceException):
    """
    exception raised for errors related to the geocode identification
    """
    def __init__(
            self,
            status_code: int,
            message: Optional[str] = None,
            details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, details=details or {}, status_code=status_code)


class GeocodeInvalidResponse(GeocodeException):
    """
    exception raised when the function identifying the latitude & longitude of an address has a too low 'confidence'
    """
    def __init__(
            self,
            status_code: int,
            message: str = "Geocode API request failed"
    ):
        self.status_code = status_code
        super().__init__(message=message, status_code=status_code)


class GeocodeConfidenceError(GeocodeException):
    """
    exception raised when the function identifying the latitude & longitude of an address has a too low 'confidence'
    """
    def __init__(
            self,
            message: str = "Geocoding confidence too low",
            details: Optional[Dict[str, Any]] = None,
            confidence_score: Optional[float] = None,
            threshold: Optional[float] = None,
    ):
        self.confidence_score = confidence_score
        self.threshold = threshold

        details = details or {}

        # Adding the confidence score & threshold to the details dictionary
        details["confidence_score"], details["required_threshold"] = confidence_score, threshold

        # in this case, the response is correct (status=200)
        super().__init__(message=message, details=details, status_code=200)
