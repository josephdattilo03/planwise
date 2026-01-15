# shared/utils/lambda_wrapper.py

import json
from shared.utils.errors import AppError


def lambda_http_handler(fn):
    def wrapper(event, context):
        try:
            return fn(event, context)

        except AppError as e:
            return e.to_response()

        except Exception:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Internal server error"}),
            }

    return wrapper
