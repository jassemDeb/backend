from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

# Language choices
LANGUAGE_CHOICES = (
    ('en', _('English')),
    ('ar', _('Arabic')),
)

class UserProfile(models.Model):
    """
    Extended user profile with language preferences
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    fullname = models.CharField(max_length=255, verbose_name=_('Full Name'))
    language_preference = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='en',
        verbose_name=_('Language Preference')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.fullname}'s Profile"

class Conversation(models.Model):
    """
    Conversation model to group related chat messages
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, verbose_name=_('Conversation Title'))
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='en',
        verbose_name=_('Conversation Language')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class ChatMessage(models.Model):
    """
    Chat message model to store user conversations
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    content = models.TextField(verbose_name=_('Message Content'))
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='en',
        verbose_name=_('Message Language')
    )
    is_user_message = models.BooleanField(default=True, verbose_name=_('Is User Message'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.content[:30]}..."

class UserSummary(models.Model):
    """
    AI-generated user summary
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='summaries')
    content = models.TextField(verbose_name=_('Summary Content'))
    language = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default='en',
        verbose_name=_('Summary Language')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'User Summaries'

    def __str__(self):
        return f"Summary for {self.user.username} ({self.language})"
