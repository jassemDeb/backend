from django.utils.translation import activate
from django.utils.deprecation import MiddlewareMixin
from .models import UserProfile
import logging
import time
from django.http import JsonResponse
from django.utils.translation import gettext as _

# Set up logging
logger = logging.getLogger(__name__)

class LanguageMiddleware(MiddlewareMixin):
    """
    Middleware to set the language based on user preference or request header
    """
    def process_request(self, request):
        language = 'en'  # Default language
        
        # Check if user is authenticated and has a language preference
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                language = profile.language_preference
            except UserProfile.DoesNotExist:
                pass
        
        # If no user profile, check Accept-Language header
        if language == 'en' and 'HTTP_ACCEPT_LANGUAGE' in request.META:
            accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
            if accept_language.startswith('ar'):
                language = 'ar'
        
        # Activate the language for this request
        activate(language)
        return None

class RateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to improve rate limit error messages and logging.
    This middleware intercepts rate limit responses and enhances them with
    more user-friendly messages and logs rate limit events.
    """
    def process_response(self, request, response):
        # Check if the response is a rate limit response (status code 429)
        if response.status_code == 429:
            # Log the rate limit event
            user_id = request.user.id if request.user.is_authenticated else 'anonymous'
            ip_address = self.get_client_ip(request)
            path = request.path
            
            logger.warning(
                f"Rate limit exceeded - User: {user_id}, IP: {ip_address}, Path: {path}"
            )
            
            # Get the user's language
            language = 'en'
            if request.user.is_authenticated:
                try:
                    profile = UserProfile.objects.get(user=request.user)
                    language = profile.language_preference
                except UserProfile.DoesNotExist:
                    pass
            
            # Activate the language for the response
            activate(language)
            
            # Create a more user-friendly response
            if path.startswith('/api/chat/ai/'):
                message = _("You've reached your AI chat limit. Please try again later.")
            elif path.startswith('/api/auth/'):
                message = _("Too many authentication attempts. Please try again later.")
            elif path.startswith('/api/chat/summary/'):
                message = _("You've reached your summary generation limit. Please try again later.")
            else:
                message = _("Too many requests. Please try again later.")
            
            # If it's a DRF response, modify it
            if hasattr(response, 'data'):
                response.data = {
                    'detail': message,
                    'status_code': 429
                }
                response._is_rendered = False
                response.render()
            # If it's a regular HttpResponse, replace it
            else:
                new_response = JsonResponse({
                    'detail': message,
                    'status_code': 429
                }, status=429)
                return new_response
                
        return response
    
    def get_client_ip(self, request):
        """Get the client IP address from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
