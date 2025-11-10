from django.contrib import admin
from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_by', 'is_public', 'created_at', 'duration')
    list_filter = ('is_public', 'uploaded_by', 'created_at')
    search_fields = ('title', 'description', 'url')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'get_embed_url', 'get_youtube_video_id', 'get_thumbnail_url')

    fieldsets = (
        ('Video Information', {
            'fields': ('title', 'description', 'uploaded_by')
        }),
        ('URLs', {
            'fields': ('url', 'embed_url', 'thumbnail')
        }),
        ('Details', {
            'fields': ('duration', 'is_public')
        }),
        ('Generated Information', {
            'fields': ('get_embed_url', 'get_youtube_video_id', 'get_thumbnail_url'),
            'classes': ('collapse',),
            'description': 'Auto-generated values from the video URL'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
