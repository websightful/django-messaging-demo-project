from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Event


@login_required
def event_list(request):
    """Display a list of events"""
    events = Event.objects.filter(is_public=True)
    return render(request, "events/event_list.html", {"events": events})


@login_required
def event_detail(request, pk):
    """Display event detail with chat room"""
    event = get_object_or_404(Event, pk=pk, is_public=True)

    context = {
        "event": event,
    }
    return render(request, "events/event_detail.html", context)
