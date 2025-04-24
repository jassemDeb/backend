from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    LogoutView,
    UserProfileView,
    UserProfileDetailView,
    ChangePasswordView,
    ChatMessageListCreateView,
    ConversationListCreateView,
    ConversationDetailView,
    UserSummaryListCreateView,
    UserSummaryDetailView,
    AIChatView,
    APIKeyTestView,
    ChatSummaryView
)

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    
    # Profile endpoints
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/detail/', UserProfileDetailView.as_view(), name='profile-detail'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Chat endpoints
    path('messages/', ChatMessageListCreateView.as_view(), name='message-list-create'),
    path('conversations/', ConversationListCreateView.as_view(), name='conversation-list-create'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    
    # AI Chat endpoint
    path('chat/ai/', AIChatView.as_view(), name='ai-chat'),
    
    # User summary endpoints
    path('summaries/', UserSummaryListCreateView.as_view(), name='summary-list-create'),
    path('summaries/<int:pk>/', UserSummaryDetailView.as_view(), name='summary-detail'),
    
    # Chat summary endpoint
    path('chat/summary/', ChatSummaryView.as_view(), name='chat-summary'),
    
    # API Key Test endpoint
    path('test/api-keys/', APIKeyTestView.as_view(), name='test-api-keys'),
]
