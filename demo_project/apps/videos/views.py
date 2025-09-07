from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Video
from django_messaging.models import ChatRoom, ChatMembership


@login_required
def video_list(request):
    """Display a list of videos"""
    videos = Video.objects.filter(is_public=True)
    return render(request, 'videos/video_list.html', {'videos': videos})


@login_required
def video_detail(request, pk):
    """Display video detail with chat room"""
    video = get_object_or_404(Video, pk=pk, is_public=True)

    # Get or create chat room for this video
    content_type = ContentType.objects.get_for_model(Video)
    room, created = ChatRoom.objects.get_or_create(
        content_type=content_type,
        object_id=video.pk,
        defaults={
            'name': f"Discussion: {video.title}",
            'is_room': True,
            'is_group': True,
        }
    )

    # Check if user is a member
    is_member = room.members.filter(id=request.user.id).exists()

    context = {
        'video': video,
        'room': room,
        'is_member': is_member,
    }
    return render(request, 'videos/video_detail.html', context)



