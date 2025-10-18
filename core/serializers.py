from rest_framework import serializers


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standardized frontend-friendly error response.
    """
    code = serializers.CharField(
        help_text="Machine-readable error code (frontend can use to select messages)."
    )
    message = serializers.CharField(
        help_text="Human-readable message that can be displayed to the user."
    )
