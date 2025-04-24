from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions

User = get_user_model()

def custom_user_authentication_rule(user, payload):
    """
    Custom authentication rule for JWT to authenticate with email instead of username
    """
    # Check if the user is active
    if user is not None and user.is_active:
        return True
    return False

class EmailBasedJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that uses email instead of username
    """
    def get_user(self, validated_token):
        """
        Attempt to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[self.user_id_claim]
        except KeyError:
            raise exceptions.AuthenticationFailed(_('Token contained no recognizable user identification'))

        try:
            user = User.objects.get(**{self.user_id_field: user_id})
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('User not found'))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_('User is inactive'))

        return user
