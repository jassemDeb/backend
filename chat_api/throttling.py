"""
Custom throttling classes for rate limiting API endpoints.
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

class AIChatRateThrottle(UserRateThrottle):
    """
    Throttle class for AI chat endpoints.
    Limits the number of requests a user can make to AI-powered endpoints.
    """
    scope = 'ai_chat'

class AuthRateThrottle(AnonRateThrottle):
    """
    Throttle class for authentication endpoints.
    Helps prevent brute force attacks on login/register endpoints.
    """
    scope = 'auth'

class ProfileUpdateRateThrottle(UserRateThrottle):
    """
    Throttle class for profile update endpoints.
    Limits how frequently users can update their profile information.
    """
    scope = 'profile_update'

class ChatSummaryRateThrottle(UserRateThrottle):
    """
    Throttle class for chat summary generation.
    Limits resource-intensive operations like generating summaries.
    """
    scope = 'chat_summary'

class BurstRateThrottle(UserRateThrottle):
    """
    Throttle class for short-term burst protection.
    Prevents rapid-fire requests in a short time window.
    """
    scope = 'burst'

class SustainedRateThrottle(UserRateThrottle):
    """
    Throttle class for long-term sustained usage.
    Ensures users don't exceed daily quotas.
    """
    scope = 'sustained'
