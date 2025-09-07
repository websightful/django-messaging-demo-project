from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Event
from django_messaging.models import ChatRoom, ChatMembership


@login_required
def event_list(request):
    """Display a list of events"""
    events = Event.objects.filter(is_public=True)
    return render(request, 'events/event_list.html', {'events': events})


@login_required
def event_detail(request, pk):
    """Display event detail with chat room"""
    event = get_object_or_404(Event, pk=pk, is_public=True)

    # Get or create chat room for this event
    content_type = ContentType.objects.get_for_model(Event)
    room, created = ChatRoom.objects.get_or_create(
        content_type=content_type,
        object_id=event.pk,
        defaults={
            'name': f"Event Chat: {event.title}",
            'is_room': True,
            'is_group': True,
        }
    )

    # Check if user is a member and attendee
    is_member = room.members.filter(id=request.user.id).exists()
    is_attendee = event.attendees.filter(id=request.user.id).exists()

    context = {
        'event': event,
        'room': room,
        'is_member': is_member,
        'is_attendee': is_attendee,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
@require_POST
def join_event(request, pk):
    """Join an event"""
    event = get_object_or_404(Event, pk=pk, is_public=True)

    if event.is_full:
        return JsonResponse({'error': 'Event is full'}, status=400)

    event.attendees.add(request.user)
    return JsonResponse({'success': True, 'attendee_count': event.attendee_count})


@login_required
@require_POST
def leave_event(request, pk):
    """Leave an event"""
    event = get_object_or_404(Event, pk=pk, is_public=True)
    event.attendees.remove(request.user)
    return JsonResponse({'success': True, 'attendee_count': event.attendee_count})
