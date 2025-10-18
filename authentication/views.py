from datetime import timedelta

from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from core.serializers import ErrorResponseSerializer

from .models import User, VerificationCode
from .serializers import (
    CheckEmailResponseSerializer,
    CheckEmailSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    LogoutResponseSerializer,
    LogoutSerializer,
    RegisterResponseSerializer,
    SendVerificationCodeResponseSerializer,
    SendVerificationCodeSerializer,
    VerifyCodeResponseSerializer,
    VerifyCodeSerializer,
    RegisterSerializer,
    UserSerializer,
)


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

@extend_schema(
    tags=["Authentication"],
    summary="Check if an email is registered",
    description=(
        "Checks whether a user account exists for the provided email address.\n\n"
        "- If the email exists → returns `exists=True` and asks for a password.\n"
        "- If the email does not exist → returns `exists=False` indicating signup flow."
    ),
    request=CheckEmailSerializer,
    responses={
        200: OpenApiResponse(
            response=CheckEmailResponseSerializer,
            description="Successful email check result."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Validation error (e.g., missing or invalid email)."
        ),
    },
    examples=[
        OpenApiExample(
            "Existing user request",
            value={"email": "registered@example.com"},
            request_only=True
        ),
        OpenApiExample(
            "Existing user response",
            value={"exists": True, "message": "User exists. Please enter your password."},
            response_only=True
        ),
        OpenApiExample(
            "New user response",
            value={"exists": False, "message": "New user. Verification code will be sent."},
            response_only=True
        ),
    ]
)
class CheckEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CheckEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()
        user_exists = User.objects.filter(email=email).exists()

        data = {
            "exists": user_exists,
            "message": "User exists. Please enter your password." if user_exists else "New user. Verification code will be sent."
        }
        return Response(data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Authentication"],
    summary="User login",
    description="Authenticate a user and return JWT tokens and user info.",
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(response=LoginResponseSerializer, description="Successful login."),
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Validation or login error.")
    },
    examples=[
        OpenApiExample(
            "Login request",
            value={"email": "user@example.com", "password": "MySecret123"},
            request_only=True
        ),
        OpenApiExample(
            "Successful login",
            value={
                "access": "eyJ0eXAiOiJKV1QiLCJh...",
                "refresh": "eyJ0eXAiOiJKV1QiLCJh...",
                "user": {"id": 1, "email": "user@example.com", "first_name": "John", "last_name": "Doe"},
                "message": "Login successful."
            },
            response_only=True
        ),
        OpenApiExample(
            "Invalid credentials",
            value={"error": {"code": "invalid_credentials", "message": "Invalid email or password."}},
            response_only=True
        ),
        OpenApiExample(
            "Email not verified",
            value={"error": {"code": "email_not_verified", "message": "Email is not verified."}},
            response_only=True
        ),
    ]
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        return Response({
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "user": UserSerializer(user).data,
            "message": "Login successful."
        }, status=status.HTTP_200_OK)
    

@extend_schema(
    tags=["Authentication"],
    summary="Send verification code for signup",
    description=(
        "Sends a verification code to the provided email address for user signup.\n\n"
        "- Invalidates any previous unused codes.\n"
        "- Generates a new code and emails it to the user.\n"
        "- Code expires after a configured time."
    ),
    request=SendVerificationCodeSerializer,
    responses={
        200: OpenApiResponse(
            response=SendVerificationCodeResponseSerializer,
            description="Verification code sent successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Validation error (e.g., email already exists)."
        ),
    },
    examples=[
        OpenApiExample(
            "Request",
            value={"email": "newuser@example.com"},
            request_only=True
        ),
        OpenApiExample(
            "Successful response",
            value={"message": "Verification code sent to email.", "expires_in_minutes": 10},
            response_only=True
        ),
        OpenApiExample(
            "Email already exists",
            value={"error": {"code": "validation_error", "message": "User with this email already exists."}},
            response_only=True
        ),
        OpenApiExample(
            "Email send failure",
            value={"error": {"code": "server_error", "message": "Failed to send email. Please try again."}},
            response_only=True
        ),
    ]
)
class SendVerificationCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        VerificationCode.objects.filter(email=email, is_used=False).update(is_used=True)

        code = VerificationCode.generate_code()
        expires_at = timezone.now() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRY_MINUTES)

        VerificationCode.objects.create(
            email=email,
            code=code,
            expires_at=expires_at
        )

        try:
            send_mail(
                subject="Your Verification Code",
                message=f"Your verification code is: {code}\n\n"
                        f"This code will expire in {settings.VERIFICATION_CODE_EXPIRY_MINUTES} minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            raise ValidationError({"detail": "Failed to send email. Please try again."})

        return Response(
            {
                "message": "Verification code sent to email.",
                "expires_in_minutes": settings.VERIFICATION_CODE_EXPIRY_MINUTES
            },
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Authentication"],
    summary="Verify signup code",
    description=(
        "Verifies a 5-digit code sent to the user's email during signup.\n\n"
        "- Marks the code as used if valid.\n"
        "- Returns `verified=True` if successful, otherwise `verified=False` with error message."
    ),
    request=VerifyCodeSerializer,
    responses={
        200: OpenApiResponse(
            response=VerifyCodeResponseSerializer,
            description="Code verified successfully."
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Invalid or expired verification code."
        ),
    },
    examples=[
        OpenApiExample(
            "Request",
            value={"email": "user@example.com", "code": "12345"},
            request_only=True
        ),
        OpenApiExample(
            "Successful verification",
            value={"verified": True, "message": "Code verified successfully. Please set your password."},
            response_only=True
        ),
        OpenApiExample(
            "Expired code",
            value={"code": "validation_error", "message": "Verification code has expired. Please request a new one."},
            response_only=True,
            status_codes=[400]
        ),
        OpenApiExample(
            "Invalid code",
            value={"code": "validation_error", "message": "Invalid verification code."},
            response_only=True,
            status_codes=[400]
        ),
    ]
)
class VerifyCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            verification = VerificationCode.objects.filter(
                email=email,
                code=code,
                is_used=False
            ).latest("created_at")

            if not verification.is_valid():
                raise ValidationError({"detail": "Verification code has expired. Please request a new one."})

            

            # Mark as used
            verification.is_used = True
            verification.save()

            return Response(
                {"verified": True, "message": "Code verified successfully. Please set your password."},
                status=status.HTTP_200_OK
            )

        except VerificationCode.DoesNotExist:
            raise ValidationError({"detail": "Invalid verification code."})


@extend_schema(
    tags=["Authentication"],
    summary="Register a new user",
    description=(
        "Registers a new user after verifying their email.\n\n"
        "- Email must be verified first.\n"
        "- Password and password_confirm must match.\n"
        "- Returns JWT tokens and user data on success."
    ),
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(response=RegisterResponseSerializer, description="User registered successfully."),
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Validation or registration error.")
    },
    examples=[
        OpenApiExample(
            "Request",
            value={
                "email": "newuser@example.com",
                "password": "Password123!",
                "password_confirm": "Password123!",
                "first_name": "John",
                "last_name": "Doe"
            },
            request_only=True
        ),
        OpenApiExample(
            "Successful registration",
            value={
                "access": "eyJ0eXAiOiJKV1QiLCJh...",
                "refresh": "eyJ0eXAiOiJKV1QiLCJh...",
                "user": {"id": 1, "email": "newuser@example.com", "first_name": "John", "last_name": "Doe"},
                "message": "Registration successful."
            },
            response_only=True
        ),
        OpenApiExample(
            "Email not verified",
            value={"code": "email_not_verified", "message": "Email not verified. Please verify your email first."},
            response_only=True,
            status_codes=[400]
        ),
        OpenApiExample(
            "User already exists",
            value={"code": "user_exists", "message": "User with this email already exists."},
            response_only=True,
            status_codes=[400]
        ),
        OpenApiExample(
            "Password mismatch",
            value={"code": "password_mismatch", "message": "Passwords do not match."},
            response_only=True,
            status_codes=[400]
        ),
    ]
)
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        verified_code = VerificationCode.objects.filter(email=email, is_used=True).order_by("-created_at").first()
        if not verified_code:
            raise ValidationError({"detail": "Email not verified. Please verify your email first."})

        if User.objects.filter(email=email).exists():
            raise ValidationError({"detail": "User with this email already exists."})

        user = serializer.save()
        tokens = get_tokens_for_user(user)

        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": UserSerializer(user).data,
                "message": "Registration successful."
            },
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    tags=["User"],
    summary="Get current authenticated user profile",
    description=(
        "Retrieves the profile information of the currently authenticated user.\n\n"
        "- Requires a valid access token in the `Authorization` header.\n"
        "- Returns user details such as `email`, `first_name`, `last_name`, and verification status."
    ),
    responses={
        200: OpenApiResponse(
            response=UserSerializer,
            description="Authenticated user profile retrieved successfully."
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Unauthorized. Missing or invalid token."
        ),
    },
    examples=[
        OpenApiExample(
            "Successful response",
            value={
                "id": 1,
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "is_verified": True,
                "date_joined": "2025-10-17T12:30:00Z"
            },
            response_only=True,
            status_codes=[200]
        ),
        OpenApiExample(
            "Unauthorized",
            value={
                "error": {
                    "code": "not_authenticated",
                    "message": "Authentication credentials were not provided."
                }
            },
            response_only=True,
            status_codes=[401]
        ),
    ]
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Authentication"],
    summary="Logout user",
    description=(
        "Invalidates the provided refresh token to log the user out.\n\n"
        "- Requires authentication.\n"
        "- Blacklists the refresh token so it cannot be used again."
    ),
    request=LogoutSerializer,
    responses={
        200: OpenApiResponse(response=LogoutResponseSerializer, description="Logout successful."),
        400: OpenApiResponse(response=ErrorResponseSerializer, description="Invalid or missing refresh token."),
        401: OpenApiResponse(response=ErrorResponseSerializer, description="Authentication required.")
    },
    examples=[
        OpenApiExample(
            "Request",
            value={"refresh": "eyJ0eXAiOiJKV1QiLCJh..."},
            request_only=True
        ),
        OpenApiExample(
            "Successful logout",
            value={"message": "Logout successful."},
            response_only=True
        ),
        OpenApiExample(
            "Missing refresh token",
            value={"code": "missing_token", "message": "Refresh token is required."},
            response_only=True,
            status_codes=[400]
        ),
        OpenApiExample(
            "Invalid token",
            value={"code": "invalid_token", "message": "Invalid token or token already blacklisted."},
            response_only=True,
            status_codes=[400]
        ),
    ]
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data.get("refresh")
        if not refresh_token:
            raise ValidationError({"detail": "Refresh token is required."})

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)
        except Exception:
            raise ValidationError({"detail": "Invalid token or token already blacklisted."})
