from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    UserView,
    GenerateQuestionsView,
    QuestionViewSet,
    UserStatsViewSet,
    AdminDashboardView,
    AdminUserViewSet
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'stats', UserStatsViewSet, basename='userstats')
router.register(r'admin/users', AdminUserViewSet, basename='admin-user')

# The API URLs are now determined automatically by the router.
# Additionally, we include the login URLs for the browsable API.
urlpatterns = [
    # Main router
    path('', include(router.urls)),

    # Authentication routes
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/user/', UserView.as_view(), name='auth-user'),

    # Question generation route
    path('generate-questions/', GenerateQuestionsView.as_view(), name='generate-questions'),

    # Admin routes
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
]
