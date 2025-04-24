from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that uses email instead of username
    """
    username_field = 'email'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields['password'] = serializers.CharField(
            style={'input_type': 'password'},
            trim_whitespace=False
        )
        
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Find user by email
            try:
                user = User.objects.filter(email=email).first()
                if user and user.check_password(password):
                    # Manually set the user for token generation
                    self.user = user
                else:
                    msg = _('Unable to log in with provided credentials.')
                    raise serializers.ValidationError(msg, code='authorization')
            except User.DoesNotExist:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        # Use the user we found by email
        refresh = self.get_token(self.user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
        return data
