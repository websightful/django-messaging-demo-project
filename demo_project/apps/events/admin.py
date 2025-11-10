from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'location', 'organizer', 'is_public', 'created_at')
    list_filter = ('is_public', 'start_date', 'organizer')
    search_fields = ('title', 'description', 'location')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'description', 'organizer')
        }),
        ('Date & Location', {
            'fields': ('start_date', 'end_date', 'location')
        }),
        ('Settings', {
            'fields': ('max_attendees', 'is_public')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
