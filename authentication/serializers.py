from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User


class CheckEmailSerializer(serializers.Serializer):
    """
    Serializer used to check if an email already exists in the system.
    """
    email = serializers.EmailField(
        help_text="The email address to check for existence."
    )

    def validate_email(self, value):
        return value.lower()


class CheckEmailResponseSerializer(serializers.Serializer):
    exists = serializers.BooleanField(
        help_text="Indicates whether a user with this email already exists."
    )
    message = serializers.CharField(
        help_text="Human-readable message for the frontend."
    )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text="Email used to log in")
    password = serializers.CharField(write_only=True, help_text="User password")

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password", "")

        if not email or not password:
            raise serializers.ValidationError({"detail": "Email and password are required."})

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError({"detail": "Invalid email or password."})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is disabled."})

        if not getattr(user, "is_verified", True):
            raise serializers.ValidationError({"detail": "Email is not verified."})

        attrs["user"] = user
        return attrs


class LoginResponseSerializer(serializers.Serializer):
    """
    Serializer for successful login response.
    """
    access = serializers.CharField(
        help_text="JWT access token."
    )
    refresh = serializers.CharField(
        help_text="JWT refresh token."
    )
    user = serializers.DictField(
        help_text="Serialized user data."
    )
    message = serializers.CharField(
        help_text="Human-readable success message."
    )


class SendVerificationCodeSerializer(serializers.Serializer):
    """
    Serializer to request a verification code for signup.
    """
    email = serializers.EmailField(help_text="Email address to send the verification code to.")

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return email


class SendVerificationCodeResponseSerializer(serializers.Serializer):
    """
    Successful response when a verification code is sent.
    """
    message = serializers.CharField(help_text="Human-readable success message.")
    expires_in_minutes = serializers.IntegerField(help_text="Time until the verification code expires.")


class VerifyCodeSerializer(serializers.Serializer):
    """
    Serializer for verifying a signup email verification code.
    """
    email = serializers.EmailField(help_text="The email associated with the verification code.")
    code = serializers.CharField(
        min_length=5, max_length=5,
        help_text="The 5-digit verification code sent to the user's email."
    )

    def validate_email(self, value):
        return value.lower()


class VerifyCodeResponseSerializer(serializers.Serializer):
    """
    Successful response after verifying a code.
    """
    verified = serializers.BooleanField(help_text="Indicates whether the verification code is valid.")
    message = serializers.CharField(help_text="Human-readable message for the frontend.")


class RegisterSerializer(serializers.Serializer):
    """
    Serializer for registering a new user.
    """
    email = serializers.EmailField(help_text="User email address.")
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        help_text="User password."
    )
    password_confirm = serializers.CharField(write_only=True, help_text="Password confirmation.")
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True, help_text="First name.")
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, help_text="Last name.")

    def validate_email(self, value):
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_verified=True
        )
        return user


class RegisterResponseSerializer(serializers.Serializer):
    """
    Successful registration response.
    """
    access = serializers.CharField(help_text="JWT access token.")
    refresh = serializers.CharField(help_text="JWT refresh token.")
    user = serializers.DictField(help_text="Serialized user data.")
    message = serializers.CharField(help_text="Success message.")


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logout request.
    """
    refresh = serializers.CharField(help_text="Refresh token to blacklist.")

class LogoutResponseSerializer(serializers.Serializer):
    """
    Successful logout response.
    """
    message = serializers.CharField(help_text="Success message.")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile information."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "is_verified", "date_joined")
        read_only_fields = ("id", "email", "is_verified", "date_joined")
