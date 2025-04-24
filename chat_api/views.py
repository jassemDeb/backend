from django.shortcuts import render
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.translation import activate
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework import permissions
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from .models import UserProfile, ChatMessage, Conversation, UserSummary
from .serializers import (
    UserSerializer, 
    UserProfileSerializer, 
    RegisterSerializer, 
    ChatMessageSerializer, 
    ConversationSerializer, 
    UserSummarySerializer
)
from .custom_serializers import EmailTokenObtainPairSerializer
from .throttling import (
    AIChatRateThrottle,
    AuthRateThrottle,
    ProfileUpdateRateThrottle,
    ChatSummaryRateThrottle,
    BurstRateThrottle,
    SustainedRateThrottle
)

import os
import random
import logging
from django.utils.translation import gettext as _
from django.utils.translation import activate, get_language

# Set up logging
logger = logging.getLogger(__name__)

# Custom throttle classes for authentication
class UserSignupRateThrottle(AuthRateThrottle):
    scope = 'auth'

class UserLoginRateThrottle(AuthRateThrottle):
    scope = 'auth'

# Language middleware
def get_user_language(request):
    """Get user language from request header or user profile"""
    if request.user.is_authenticated:
        try:
            return request.user.profile.language_preference
        except UserProfile.DoesNotExist:
            pass
    
    # Check header
    lang_header = request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')
    if lang_header.startswith('ar'):
        return 'ar'
    return 'en'

# Authentication views
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [UserSignupRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Get user language
        language = serializer.validated_data.get('language_preference', 'en')
        activate(language)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data,
            'message': _('User registered successfully')
        }, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [UserLoginRateThrottle]
    serializer_class = EmailTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get user and activate their language
            email = request.data.get('email')
            try:
                user = User.objects.get(email=email)
                try:
                    profile = UserProfile.objects.get(user=user)
                    language = profile.language_preference
                    activate(language)
                    
                    # Add user data to response
                    response.data['user'] = UserSerializer(user).data
                    response.data['language'] = language
                    response.data['message'] = _('Login successful')
                    
                except UserProfile.DoesNotExist:
                    # Create profile with default language if it doesn't exist
                    UserProfile.objects.create(user=user, fullname=email.split('@')[0], language_preference='en')
                    
            except User.DoesNotExist:
                pass
                
        return response

class LogoutView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": _("Logout successful")}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# User Profile views
class UserProfileDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ProfileUpdateRateThrottle]
    
    def get(self, request):
        """Get the user's profile information"""
        user = request.user
        try:
            profile = UserProfile.objects.get(user=user)
            
            # Combine user and profile data
            profile_data = {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'fullname': profile.fullname,
                'language_preference': profile.language_preference,
                'date_joined': user.date_joined,
                'last_login': user.last_login
            }
            
            return Response(profile_data)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'User profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def patch(self, request):
        """Update the user's profile information"""
        user = request.user
        
        # Get user language and activate it
        language = get_user_language(request)
        activate(language)
        
        try:
            profile = UserProfile.objects.get(user=user)
            
            # Initialize response data
            response_data = {}
            errors = {}
            
            # Update user fields
            if 'first_name' in request.data:
                user.first_name = request.data['first_name']
            if 'last_name' in request.data:
                user.last_name = request.data['last_name']
            if 'email' in request.data:
                # Check if email is already taken by another user
                if User.objects.exclude(id=user.id).filter(email=request.data['email']).exists():
                    errors['email'] = _('This email is already in use.')
                else:
                    user.email = request.data['email']
            
            # Update profile fields
            if 'fullname' in request.data:
                # Validate fullname
                if not request.data['fullname'] or len(request.data['fullname'].strip()) < 3:
                    errors['fullname'] = _('Full name must be at least 3 characters long.')
                else:
                    profile.fullname = request.data['fullname']
                    
                    # Also update first_name and last_name if no errors
                    if 'fullname' not in errors:
                        name_parts = request.data['fullname'].split(' ', 1)
                        user.first_name = name_parts[0]
                        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
                
            if 'language_preference' in request.data:
                # Validate language
                if request.data['language_preference'] not in ['en', 'ar']:
                    errors['language_preference'] = _('Language must be either "en" or "ar".')
                else:
                    profile.language_preference = request.data['language_preference']
                    # Activate the new language
                    activate(request.data['language_preference'])
            
            # Return errors if any
            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Save changes
            user.save()
            profile.save()
            
            # Return updated profile data
            profile_data = {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'fullname': profile.fullname,
                'language_preference': profile.language_preference,
                'date_joined': user.date_joined,
                'last_login': user.last_login
            }
            
            return Response({
                'data': profile_data,
                'message': _('Profile updated successfully')
            })
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': _('User profile not found.')},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}")
            return Response(
                {'detail': _('An error occurred while updating your profile.')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Keep the existing class for compatibility
class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserProfileSerializer
    
    def get_object(self):
        return self.request.user.userprofile

    def get(self, request, *args, **kwargs):
        # Activate user's language preference
        profile = self.get_object()
        activate(profile.language_preference)
        return super().get(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Activate updated language preference
        activate(instance.language_preference)
        
        return Response(serializer.data)

# Chat Message views
class ChatMessageListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ChatMessageSerializer
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]
    
    def get_queryset(self):
        # Get user's language from profile
        language = get_user_language(self.request)
        activate(language)
        
        # Filter messages by user and optionally by language
        queryset = ChatMessage.objects.filter(user=self.request.user)
        lang_filter = self.request.query_params.get('language')
        if lang_filter:
            queryset = queryset.filter(language=lang_filter)
        return queryset
    
    def perform_create(self, serializer):
        # Set user and language automatically
        language = get_user_language(self.request)
        serializer.save(
            user=self.request.user,
            language=language
        )

# Conversation views
class ConversationListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ConversationSerializer
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]
    
    def get_queryset(self):
        # Get user's language from profile
        language = get_user_language(self.request)
        activate(language)
        
        # Filter conversations by user and optionally by language
        queryset = Conversation.objects.filter(user=self.request.user)
        lang_filter = self.request.query_params.get('language')
        if lang_filter:
            queryset = queryset.filter(language=lang_filter)
        return queryset
    
    def perform_create(self, serializer):
        # Set user and language automatically
        language = get_user_language(self.request)
        serializer.save(
            user=self.request.user,
            language=language
        )

class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ConversationSerializer
    throttle_classes = [BurstRateThrottle]
    
    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        # Activate user's language preference
        language = get_user_language(request)
        activate(language)
        return super().get(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        # Activate user's language preference
        language = get_user_language(request)
        activate(language)
        
        try:
            conversation = self.get_object()
            
            # Delete all associated messages first
            messages_count = ChatMessage.objects.filter(conversation=conversation).count()
            ChatMessage.objects.filter(conversation=conversation).delete()
            
            # Then delete the conversation
            conversation.delete()
            
            return Response({
                'success': True,
                'message': _('Conversation and its messages deleted successfully'),
                'deleted_messages_count': messages_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {str(e)}")
            return Response({
                'success': False,
                'message': _('Failed to delete conversation'),
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# User Summary views
class UserSummaryListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSummarySerializer
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]
    
    def get_queryset(self):
        # Get user's language from profile
        language = get_user_language(self.request)
        activate(language)
        
        # Filter summaries by user and optionally by language
        queryset = UserSummary.objects.filter(user=self.request.user)
        lang_filter = self.request.query_params.get('language')
        if lang_filter:
            queryset = queryset.filter(language=lang_filter)
        return queryset
    
    def perform_create(self, serializer):
        # Set user and language automatically
        language = get_user_language(self.request)
        serializer.save(
            user=self.request.user,
            language=language
        )

class UserSummaryDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSummarySerializer
    throttle_classes = [BurstRateThrottle]
    
    def get_queryset(self):
        return UserSummary.objects.filter(user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        # Activate user's language preference
        language = get_user_language(request)
        activate(language)
        return super().get(request, *args, **kwargs)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Change the user's password"""
        user = request.user
        
        # Validate current password
        current_password = request.data.get('current_password')
        if not user.check_password(current_password):
            return Response(
                {'current_password': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate new password
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        if new_password != confirm_password:
            return Response(
                {'confirm_password': 'Passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate password strength
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {'new_password': list(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return Response({'detail': 'Password changed successfully.'})

# AI Chat views
class AIChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIChatRateThrottle]
    
    def post(self, request):
        """Generate a response from the selected AI model and save the conversation"""
        user = request.user
        message_text = request.data.get('message', '')
        conversation_id = request.data.get('conversation_id', None)
        language = request.data.get('language', 'en')
        model_id = request.data.get('model', 'lamini-t5')  # Default model
        
        # Define available models with their Hugging Face paths
        AVAILABLE_MODELS = {
            'lamini-t5': {
                'path': 'MBZUAI/LaMini-Flan-T5-248M',
                'params': {
                    'max_length': 100,
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'do_sample': True
                }
            },
            'deepseek': {
                'path': 'deepseek-ai/deepseek-coder-1.3b-instruct',
                'params': {
                    'max_length': 100,
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'do_sample': True
                }
            },
            'blenderbot-400M': {
                'path': 'facebook/blenderbot-400M-distill',
                'params': {
                    'max_length': 100,
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'do_sample': True
                }
            }
        }
        
        # Default responses for different languages
        DEFAULT_RESPONSES = {
            'en': {
                'greeting': "Hello! I'm an AI assistant. How can I help you today?",
                'fallback': "I'm sorry, I couldn't generate a proper response. Could you try asking something else?",
                'understanding': "I'm sorry, I don't understand. Could you rephrase that?",
                'error': "Sorry, there was an error processing your request. Please try again."
            },
            'ar': {
                'greeting': "مرحبًا! أنا مساعد ذكاء اصطناعي. كيف يمكنني مساعدتك اليوم؟",
                'fallback': "آسف، لم أتمكن من إنشاء استجابة مناسبة. هل يمكنك تجربة سؤال آخر؟",
                'understanding': "آسف، لم أفهم. هل يمكنك إعادة صياغة ذلك؟",
                'error': "عذرًا، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى."
            }
        }
        
        # Simulated responses for when the API is down
        SIMULATED_RESPONSES = {
            'en': {
                'greeting': [
                    "Hello! How can I assist you today?",
                    "Hi there! What can I help you with?",
                    "Greetings! How may I be of service?"
                ],
                'about': [
                    "I'm an AI assistant designed to help answer your questions and provide information.",
                    "I'm a language model trained to assist with various tasks and answer questions.",
                    "I'm your AI assistant, ready to help with information and tasks."
                ],
                'general': [
                    "That's an interesting question. Let me think about that...",
                    "I understand what you're asking. Here's what I know about that topic...",
                    "Thanks for your question. I'd be happy to help with that.",
                    "I appreciate your question. Let me provide some information on that.",
                    "That's a good point. Here's my perspective on that matter."
                ]
            },
            'ar': {
                'greeting': [
                    "مرحبًا! كيف يمكنني مساعدتك اليوم؟",
                    "أهلاً! بماذا يمكنني مساعدتك؟",
                    "تحياتي! كيف يمكنني خدمتك؟"
                ],
                'about': [
                    "أنا مساعد ذكاء اصطناعي مصمم للمساعدة في الإجابة على أسئلتك وتقديم المعلومات.",
                    "أنا نموذج لغوي تم تدريبه للمساعدة في مختلف المهام والإجابة على الأسئلة.",
                    "أنا مساعدك الذكي، جاهز للمساعدة في المعلومات والمهام."
                ],
                'general': [
                    "هذا سؤال مثير للاهتمام. دعني أفكر في ذلك...",
                    "أفهم ما تسأل عنه. إليك ما أعرفه عن هذا الموضوع...",
                    "شكرًا على سؤالك. يسعدني المساعدة في ذلك.",
                    "أقدر سؤالك. دعني أقدم بعض المعلومات حول ذلك.",
                    "هذه نقطة جيدة. إليك وجهة نظري في هذه المسألة."
                ]
            }
        }
        
        # Special handling for Arabic greetings - models often struggle with these
        def get_simulated_response(message, lang='en'):
            """Generate a simulated response when the API is down"""
            import random
            
            # Check for greetings
            greeting_words = {
                'en': ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon'],
                'ar': ['مرحبا', 'أهلا', 'السلام عليكم', 'صباح الخير', 'مساء الخير']
            }
            
            # Check for questions about identity
            identity_words = {
                'en': ['who are you', 'what are you', 'tell me about yourself', 'your name'],
                'ar': ['من أنت', 'ما أنت', 'أخبرني عن نفسك', 'ما هو اسمك']
            }
            
            message_lower = message.lower()
            
            # Select response category
            if any(word in message_lower for word in greeting_words.get(lang, greeting_words['en'])):
                category = 'greeting'
            elif any(word in message_lower for word in identity_words.get(lang, identity_words['en'])):
                category = 'about'
            else:
                category = 'general'
            
            # Get responses for the selected language and category
            responses = SIMULATED_RESPONSES.get(lang, SIMULATED_RESPONSES['en']).get(category, SIMULATED_RESPONSES['en']['general'])
            
            # Return a random response from the category
            return random.choice(responses)
        
        if not message_text:
            return Response(
                {'detail': 'Message text is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if model is valid
        if model_id not in AVAILABLE_MODELS:
            return Response(
                {'detail': f'Invalid model. Available models: {", ".join(AVAILABLE_MODELS.keys())}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get model configuration
        model_config = AVAILABLE_MODELS[model_id]
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=user)
            except Conversation.DoesNotExist:
                return Response(
                    {'detail': 'Conversation not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Create a new conversation
            conversation = Conversation.objects.create(
                user=user,
                title=message_text[:50] + '...' if len(message_text) > 50 else message_text,
                language=language
            )
        
        # Save user message
        user_message = ChatMessage.objects.create(
            user=user,
            content=message_text,
            language=language,
            is_user_message=True,
            conversation=conversation  # Associate with conversation
        )
        
        # Call Hugging Face API
        import requests
        import json
        from django.conf import settings
            
        # Prepare headers based on the model
        if model_id == 'deepseek':
            API_URL = f"https://api-inference.huggingface.co/models/{model_config['path']}"
            headers = {
                "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
        else:
            API_URL = f"https://api-inference.huggingface.co/models/{model_config['path']}"
            headers = {
                "Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}",
                "Content-Type": "application/json"
            }
        
        # Prepare payload based on model
        if model_id == 'deepseek':
            # For deepseek, we need to get conversation history
            conversation_messages = ChatMessage.objects.filter(
                user=user, 
                conversation=conversation
            ).order_by('created_at')
            # Take last 5 messages to avoid context length issues
            recent_messages = conversation_messages.order_by('-created_at')[:5]
            recent_messages = sorted(recent_messages, key=lambda x: x.created_at)
            
            # Use appropriate language markers based on the language
            user_prefix = "المستخدم" if language == 'ar' else "User"
            bot_prefix = "الروبوت" if language == 'ar' else "Bot"
            
            conversation_history = "\n".join([
                f"{user_prefix if msg.is_user_message else bot_prefix}: {msg.content}" 
                for msg in recent_messages
            ])
            
            payload = {
                "inputs": f"{conversation_history}\n{user_prefix}: {message_text}\n{bot_prefix}:",
                "parameters": model_config['params']
            }
        else:
            # For other models, just send the message
            payload = {
                "inputs": message_text,
                "parameters": model_config['params']
            }
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            
            if response.status_code != 200:
                # Log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Hugging Face API error: {response.status_code} - {response.text[:200]}")
                
                # Return a fallback response instead of an error
                # This way the chat can continue even if the API is down
                ai_response = get_simulated_response(message_text, language)
                
                # Save the fallback response
                ai_message = ChatMessage.objects.create(
                    user=user,
                    content=ai_response,
                    language=language,
                    is_user_message=False,
                    conversation=conversation
                )
                
                # Update conversation's last_updated
                conversation.save()
                
                return Response({
                    'conversation_id': conversation.id,
                    'model': model_id,
                    'user_message': {
                        'id': user_message.id,
                        'content': user_message.content,
                        'created_at': user_message.created_at
                    },
                    'ai_response': {
                        'id': ai_message.id,
                        'content': ai_message.content,
                        'created_at': ai_message.created_at
                    }
                })
            
            # Check if this is a greeting in Arabic
            arabic_greetings = ['مرحبا', 'السلام عليكم', 'أهلا', 'صباح الخير', 'مساء الخير', 'كيف حالك', 'من أنت']
            is_arabic_greeting = language == 'ar' and any(greeting in message_text.lower() for greeting in arabic_greetings)
            
            # Extract AI response based on model
            result = response.json()
            
            # Special handling for Arabic greetings - models often struggle with these
            if is_arabic_greeting:
                # For greeting messages in Arabic, use our predefined responses
                if 'من أنت' in message_text.lower():
                    ai_response = "أنا مساعد ذكاء اصطناعي مصمم للمساعدة في الإجابة على أسئلتك وتقديم المعلومات. كيف يمكنني مساعدتك اليوم؟"
                elif any(greeting in message_text.lower() for greeting in ['كيف حالك', 'كيفك']):
                    ai_response = "أنا بخير، شكراً على سؤالك! كيف يمكنني مساعدتك اليوم؟"
                else:
                    ai_response = DEFAULT_RESPONSES[language]['greeting']
            elif model_id == 'lamini-t5':
                # LaMini-T5 is better at handling different languages
                ai_response = result[0].get('generated_text', '').strip()
                # If response is empty, provide a fallback in the appropriate language
                if not ai_response:
                    ai_response = DEFAULT_RESPONSES[language]['fallback']
            elif model_id == 'deepseek':
                generated_text = result[0].get('generated_text', '').strip()
                
                # deepseek tends to return the conversation history
                # We need to extract only the new response
                
                # First, check if our last message is in the response
                last_message_marker = f"{user_prefix}: {message_text}"
                if last_message_marker in generated_text:
                    # Extract everything after the last occurrence of our message
                    parts = generated_text.split(last_message_marker)
                    ai_response = parts[-1].strip()
                    
                    # If the response is empty or just contains the user message again
                    if not ai_response or f"{user_prefix}:" in ai_response:
                        # Fallback to a simple response in the appropriate language
                        ai_response = DEFAULT_RESPONSES[language]['fallback']
                else:
                    # If we can't find our message, just take the last line
                    lines = [line for line in generated_text.split('\n') if line.strip() and not line.strip().startswith(f"{user_prefix}:")]
                    if lines:
                        ai_response = lines[-1]
                    else:
                        # Fallback response in the appropriate language
                        ai_response = DEFAULT_RESPONSES[language]['understanding']
                
                # Clean up any remaining "Bot:" prefix
                ai_response = ai_response.replace(f"{bot_prefix}:", '').strip()
            else:  # blenderbot (keeping as fallback)
                ai_response = result[0].get('generated_text', '')
                # If response is empty, provide a fallback in the appropriate language
                if not ai_response:
                    ai_response = DEFAULT_RESPONSES[language]['fallback']
            
            # Save AI response
            ai_message = ChatMessage.objects.create(
                user=user,
                content=ai_response,
                language=language,
                is_user_message=False,
                conversation=conversation  # Associate with conversation
            )
            
            # Update conversation's last_updated
            conversation.save()
            
            return Response({
                'conversation_id': conversation.id,
                'model': model_id,
                'user_message': {
                    'id': user_message.id,
                    'content': user_message.content,
                    'created_at': user_message.created_at
                },
                'ai_response': {
                    'id': ai_message.id,
                    'content': ai_message.content,
                    'created_at': ai_message.created_at
                }
            })
            
        except Exception as e:
            # Log the error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calling Hugging Face API: {str(e)}")
            
            # Return a simulated response
            ai_response = get_simulated_response(message_text, language)
            
            # Save the simulated response
            ai_message = ChatMessage.objects.create(
                user=user,
                content=ai_response,
                language=language,
                is_user_message=False,
                conversation=conversation
            )
            
            # Update conversation's last_updated
            conversation.save()
            
            return Response({
                'conversation_id': conversation.id,
                'model': model_id,
                'user_message': {
                    'id': user_message.id,
                    'content': user_message.content,
                    'created_at': user_message.created_at
                },
                'ai_response': {
                    'id': ai_message.id,
                    'content': ai_message.content,
                    'created_at': ai_message.created_at
                }
            })

class APIKeyTestView(APIView):
    """Test endpoint to verify API keys are working"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings
        
        # Check if API keys are set
        huggingface_key = settings.HUGGINGFACE_API_KEY
        deepseek_key = settings.DEEPSEEK_API_KEY
        
        # Mask the keys for security (show only first and last 4 characters)
        def mask_key(key):
            if not key or len(key) < 8:
                return "Not set or too short"
            return f"{key[:4]}...{key[-4:]}"
        
        huggingface_masked = mask_key(huggingface_key)
        deepseek_masked = mask_key(deepseek_key)
        
        return Response({
            'huggingface_api_key': huggingface_masked,
            'deepseek_api_key': deepseek_masked,
            'huggingface_key_set': bool(huggingface_key),
            'deepseek_key_set': bool(deepseek_key)
        })

class ChatSummaryView(APIView):
    """Generate a summary of the user's chat history using DeepSeek model with improved prompting"""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ChatSummaryRateThrottle]
    
    def post(self, request):
        """Generate a summary of the user's chat history"""
        user = request.user
        language = request.data.get('language', 'en')
        max_messages = int(request.data.get('max_messages', 50))  # Limit number of messages to summarize
        
        # Get user's chat messages
        messages = ChatMessage.objects.filter(user=user).order_by('-created_at')[:max_messages]
        
        if not messages:
            return Response({
                'summary': 'No chat history available to summarize.' if language == 'en' else 'لا يوجد سجل محادثات متاح للتلخيص.'
            })
        
        try:
            # Group messages by conversation
            conversation_messages = {}
            for msg in messages:
                conv_id = msg.conversation_id if msg.conversation else 'no_conversation'
                if conv_id not in conversation_messages:
                    conversation_messages[conv_id] = []
                conversation_messages[conv_id].append(msg)
            
            # Format messages for analysis
            formatted_conversations = []
            for conv_id, msgs in conversation_messages.items():
                # Sort messages by creation time
                msgs.sort(key=lambda x: x.created_at)
                
                # Format this conversation
                conversation_text = ""
                for msg in msgs:
                    role = "User" if msg.is_user_message else "AI"
                    conversation_text += f"{role}: {msg.content}\n"
                
                formatted_conversations.append({
                    "id": conv_id,
                    "text": conversation_text,
                    "first_message": msgs[0].content if msgs else "",
                    "message_count": len(msgs),
                    "user_message_count": sum(1 for m in msgs if m.is_user_message),
                    "ai_message_count": sum(1 for m in msgs if not m.is_user_message),
                })
            
            # Call DeepSeek API for intelligent summarization
            import requests
            
            API_URL = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {os.environ.get('DEEPSEEK_API_KEY')}",
                "Content-Type": "application/json"
            }
            
            # Create a detailed and specific prompt for the DeepSeek model
            system_prompt = """You are an AI assistant that analyzes chat history and creates detailed user summaries.

Your task is to analyze the provided chat conversations and create a structured summary that includes:

1. User Interests: Key topics and themes the user frequently discusses or asks about. DO NOT list individual messages as interests. Instead, identify patterns and recurring themes.

2. Recent Activity: What the user has been working on or discussing recently. Focus on actual activities and projects, not just conversation topics.

Format the summary with clear sections and bullet points. Be specific and mention actual topics, technologies, or concepts the user has discussed. Do not make up information that is not in the chat history.

IMPORTANT: Do not list individual messages as interests or activities unless they represent a genuine interest or activity. Look for patterns across messages."""

            # Add language-specific instructions
            if language == 'ar':
                system_prompt += "\nPlease write the summary in Arabic, using appropriate RTL formatting."
            
            # Create a detailed analysis of the conversations for the model
            conversation_analysis = ""
            for i, conv in enumerate(formatted_conversations):
                conversation_analysis += f"Conversation {i+1}:\n{conv['text']}\n\n"
            
            # Add statistics to help the model
            stats = f"""
Chat Statistics:
- Total conversations: {len(conversation_messages)}
- Total messages: {sum(len(msgs) for msgs in conversation_messages.values())}
- User messages: {sum(sum(1 for m in msgs if m.is_user_message) for msgs in conversation_messages.values())}
- AI responses: {sum(sum(1 for m in msgs if not m.is_user_message) for msgs in conversation_messages.values())}
"""
            
            # Prepare the messages for the API with a very specific user instruction
            user_instruction = f"""Analyze these conversations and create a detailed user summary as specified.
Focus on identifying genuine interests and activities, not just listing messages.
If you can't identify clear interests or activities, say so rather than listing generic or meaningless items.

{conversation_analysis}

{stats}

Format your response with:
1. "User Interests:" section with bullet points of genuine interests
2. "Recent Activity:" section with bullet points of actual activities"""

            messages_for_api = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_instruction}
            ]
            
            payload = {
                "model": "deepseek-coder-1.3b-instruct",
                "messages": messages_for_api,
                "temperature": 0.2,
                "max_tokens": 1000
            }
            
            response = requests.post(API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                summary_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                if not summary_text:
                    logger.warning(f"Couldn't extract summary from DeepSeek response: {result}")
                    # Fall back to our basic summary
                    summary_text = self._generate_basic_summary(conversation_messages, language)
            else:
                # If API call fails, generate a simple summary
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                summary_text = self._generate_basic_summary(conversation_messages, language)
            
            # Save the summary
            user_summary = UserSummary.objects.create(
                user=user,
                content=summary_text,
                language=language
            )
            
            return Response({
                'summary': summary_text,
                'summary_id': user_summary.id,
                'conversation_count': len(conversation_messages),
                'message_count': {
                    'user': sum(conv['user_message_count'] for conv in formatted_conversations),
                    'ai': sum(conv['ai_message_count'] for conv in formatted_conversations)
                }
            })
                
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return Response({
                'error': 'Failed to generate summary',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _generate_basic_summary(self, conversation_messages, language):
        """Generate a basic summary if the API call fails"""
        # Count message types
        user_message_count = 0
        ai_message_count = 0
        
        for conv_id, msgs in conversation_messages.items():
            # Count message types
            for msg in msgs:
                if msg.is_user_message:
                    user_message_count += 1
                else:
                    ai_message_count += 1
        
        # Generate summary based on language
        if language == 'ar':
            summary = "ملخص المستخدم\n\n"
            
            summary += "اهتمامات المستخدم:\n\n"
            summary += "• لم يتم تحديد اهتمامات محددة من المحادثات.\n"
            
            summary += "\nالنشاط الأخير:\n\n"
            summary += f"• قام بإرسال {user_message_count} رسالة وتلقى {ai_message_count} رد من الذكاء الاصطناعي.\n"
            if len(conversation_messages) > 1:
                summary += f"• شارك في {len(conversation_messages)} محادثات مختلفة.\n"
            else:
                summary += "• شارك في محادثة واحدة.\n"
        else:
            summary = "User Summary\n\n"
            
            summary += "User Interests:\n\n"
            summary += "• No specific interests identified from conversations.\n"
            
            summary += "\nRecent Activity:\n\n"
            summary += f"• Sent {user_message_count} messages and received {ai_message_count} AI responses.\n"
            if len(conversation_messages) > 1:
                summary += f"• Engaged in {len(conversation_messages)} different conversations.\n"
            else:
                summary += "• Engaged in one conversation.\n"
        
        return summary
