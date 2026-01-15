import json

class AppError(Exception):
    status_code = 500
    message = "Internal server error"

    def to_response(self):
        return {
            "statusCode": self.status_code,
            "body": json.dumps({"error": self.message}),
        }

class InvalidEventTimeError(AppError):
    status_code = 400
    message = "Event start time must be before end time"

class NotFoundError(AppError):
    status_code = 404

class BadRequestError(AppError):
    status_code = 400


class ValidationAppError(BadRequestError):
    def __init__(self, details):
        self.details = details
        self.message = "Validation failed"

    def to_response(self):
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": self.message,
                "details": self.details,
            }),
        }

