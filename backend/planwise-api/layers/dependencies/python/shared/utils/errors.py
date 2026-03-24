import json
from typing import Any


class AppError(Exception):
    status_code = 500
    message = "Internal server error"

    def to_response(self) -> dict[str, Any]:
        return {
            "statusCode": self.status_code,
            "body": json.dumps({"error": self.message}),
        }


class InvalidEventTimeError(AppError):
    status_code = 400
    message = "Event start time must be before end time"


class NoUpdatesProvidedError(AppError):
    status_code = 400
    message = "No updates provided"


class NotFoundError(AppError):
    status_code = 404


class BadRequestError(AppError):
    status_code = 400


class GoogleOAuthConfigurationError(AppError):
    status_code = 503
    message = "Google OAuth is not configured"


class GoogleCalendarAuthError(AppError):
    status_code = 400
    message = "Google Calendar is not connected for this user"


class ValidationAppError(BadRequestError):
    def __init__(self, details: list[dict[str, Any]]) -> None:
        super().__init__()
        self.details = details
        self.message = "Validation failed"

    def to_response(self) -> dict[str, Any]:
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": self.message,
                    "details": self.details,
                }
            ),
        }
