from django.contrib import admin
from .models import UserProfile, ChatMessage, Conversation, UserSummary

# Register models with custom admin displays
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'language_preference', 'created_at')
    list_filter = ('language_preference',)
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'created_at'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'content', 'language', 'is_user_message', 'created_at')
    list_filter = ('language', 'is_user_message')
    search_fields = ('user__username', 'content')
    date_hierarchy = 'created_at'

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'language', 'created_at', 'updated_at')
    list_filter = ('language',)
    search_fields = ('title', 'user__username')
    date_hierarchy = 'created_at'

@admin.register(UserSummary)
class UserSummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'language', 'created_at')
    list_filter = ('language',)
    search_fields = ('user__username', 'content')
    date_hierarchy = 'created_at'
