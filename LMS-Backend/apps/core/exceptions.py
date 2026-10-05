"""Business-rule errors and a single error envelope for the whole API.

Every error response looks like: {"error": {"code": "...", "message": "...", "fields": {...}?}}
"""

from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessRuleError(Exception):
    """Raised by a service function when a business rule blocks an action.

    Always surfaced as HTTP 400 with a specific machine-readable `code`
    (e.g. MEMBER_BLOCKED, LOAN_LIMIT_REACHED, NO_COPIES_AVAILABLE).
    """

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def api_exception_handler(exc, context):
    if isinstance(exc, BusinessRuleError):
        return Response({"error": {"code": exc.code, "message": exc.message}}, status=400)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, drf_exceptions.ValidationError):
        fields = response.data if isinstance(response.data, dict) else {"detail": response.data}
        response.data = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "One or more fields are invalid.",
                "fields": fields,
            }
        }
        return response

    code = {
        401: "NOT_AUTHENTICATED",
        403: "PERMISSION_DENIED",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        429: "THROTTLED",
    }.get(response.status_code, "ERROR")

    detail = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(exc)
    response.data = {"error": {"code": code, "message": str(detail)}}
    return response
