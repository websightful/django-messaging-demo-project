from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import Video


@login_required
def video_list(request):
    """Display a list of videos"""
    videos = Video.objects.filter(is_public=True)
    return render(request, "videos/video_list.html", {"videos": videos})


@login_required
def video_detail(request, pk):
    """Display video detail with chat room"""
    video = get_object_or_404(Video, pk=pk, is_public=True)

    context = {
        "video": video,
    }
    return render(request, "videos/video_detail.html", context)
