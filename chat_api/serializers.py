from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile, ChatMessage, Conversation, UserSummary


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'language_preference', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    fullname = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    language_preference = serializers.ChoiceField(choices=[('en', 'English'), ('ar', 'Arabic')], default='en')

    class Meta:
        model = User
        fields = ('email', 'fullname', 'password', 'password2', 'language_preference')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Check if email already exists
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})
            
        return attrs

    def create(self, validated_data):
        fullname = validated_data.pop('fullname')
        language_preference = validated_data.pop('language_preference')
        validated_data.pop('password2')
        
        # Split fullname into first_name and last_name
        name_parts = fullname.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create username from email (Django User model requires username)
        username = validated_data['email'].split('@')[0]
        base_username = username
        counter = 1
        
        # Ensure username is unique
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create user
        user = User.objects.create(
            username=username,
            email=validated_data['email'],
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(validated_data['password'])
        user.save()

        # Create user profile with fullname and language preference
        UserProfile.objects.create(
            user=user,
            fullname=fullname,
            language_preference=language_preference
        )
        
        return user


class ChatMessageSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = ('id', 'user', 'username', 'content', 'language', 'is_user_message', 'created_at')
        read_only_fields = ('id', 'created_at', 'username')
    
    def get_username(self, obj):
        return obj.user.username


class ConversationSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ('id', 'user', 'title', 'language', 'created_at', 'updated_at', 'messages')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_messages(self, obj):
        # Get messages related to this conversation
        messages = ChatMessage.objects.filter(conversation=obj).order_by('created_at')
        return ChatMessageSerializer(messages, many=True).data


class UserSummarySerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSummary
        fields = ('id', 'user', 'username', 'content', 'language', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at', 'username')
    
    def get_username(self, obj):
        return obj.user.username
