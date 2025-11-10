from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User


class Video(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    url = models.URLField(help_text="YouTube, Vimeo, or other video URL")
    embed_url = models.URLField(blank=True, help_text="YouTube embed URL (e.g., https://www.youtube.com/embed/VIDEO_ID)")
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

    def get_embed_url(self):
        """Generate embed URL from regular YouTube URL"""
        if self.embed_url:
            return self.embed_url

        if 'youtube.com/watch?v=' in self.url:
            video_id = self.url.split('watch?v=')[1].split('&')[0]
            return f"https://www.youtube.com/embed/{video_id}"
        elif 'youtu.be/' in self.url:
            video_id = self.url.split('youtu.be/')[1].split('?')[0]
            return f"https://www.youtube.com/embed/{video_id}"

        return None

    def get_youtube_video_id(self):
        """Extract YouTube video ID from URL"""
        if 'youtube.com/watch?v=' in self.url:
            return self.url.split('watch?v=')[1].split('&')[0]
        elif 'youtu.be/' in self.url:
            return self.url.split('youtu.be/')[1].split('?')[0]
        return None

    def get_thumbnail_url(self):
        """Get thumbnail URL - use custom thumbnail or generate from YouTube"""
        if self.thumbnail:
            return self.thumbnail

        video_id = self.get_youtube_video_id()
        if video_id:
            return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

        return None



