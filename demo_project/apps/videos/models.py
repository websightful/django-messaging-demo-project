from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User


class Video(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(help_text="YouTube, Vimeo, or other video URL")
    thumbnail = models.URLField(blank=True, help_text="Thumbnail image URL")
    duration = models.DurationField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_videos')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('videos:detail', kwargs={'pk': self.pk})



