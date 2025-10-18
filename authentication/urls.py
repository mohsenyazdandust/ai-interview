from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CheckEmailView,
    LoginView,
    SendVerificationCodeView,
    VerifyCodeView,
    RegisterView,
    MeView,
    LogoutView
)

urlpatterns = [
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('send-code/', SendVerificationCodeView.as_view(), name='send-code'),
    path('verify-code/', VerifyCodeView.as_view(), name='verify-code'),
    path('register/', RegisterView.as_view(), name='register'),
    path('me/', MeView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
