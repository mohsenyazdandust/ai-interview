# core/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


EXCEPTION_CODE_MAP = {
    "ValidationError": "validation_error",
    "NotAuthenticated": "not_authenticated",
    "AuthenticationFailed": "invalid_credentials",
    "PermissionDenied": "permission_denied",
    "NotFound": "not_found",
    "MethodNotAllowed": "method_not_allowed",
}


def custom_exception_handler(exc, context):
    """
    Wrap all DRF exceptions in a unified frontend-friendly format:
    {
        "code": "machine_readable_code",
        "message": "Human-readable message"
    }
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Determine a consistent code
        code = EXCEPTION_CODE_MAP.get(exc.__class__.__name__, exc.__class__.__name__)

        # Determine message
        message = "Validation failed."

        if isinstance(response.data, dict):
            # DRF validation errors can be dict or list
            if "detail" in response.data:
                # `detail` can be a string or list
                if isinstance(response.data["detail"], list):
                    message = " ".join(str(i) for i in response.data["detail"])
                else:
                    message = str(response.data["detail"])
            else:
                # Take the first error message if dict of field errors
                first_error = next(iter(response.data.values()))
                if isinstance(first_error, list):
                    message = " ".join(str(i) for i in first_error)
                else:
                    message = str(first_error)
        elif isinstance(response.data, list):
            # Rare case: DRF returns a list of errors
            message = " ".join(str(i) for i in response.data)
        else:
            message = str(response.data)
        
        return Response(
            {"code": code, "message": message},
            status=response.status_code
        )

    # Fallback for unhandled exceptions
    return Response(
        {"code": "server_error", "message": str(exc)},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
