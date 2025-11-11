from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q


def person_list(request):
    """
    Display a list of active users with search functionality.
    """
    search_query = request.GET.get('search', '')

    # Get active users (is_active=True)
    users = User.objects.filter(is_active=True)

    # Apply search filter if provided
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Order by username
    users = users.order_by('username')

    # Pagination
    paginator = Paginator(users, 20)  # Show 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'users_with_avatars': page_obj,
        'search_query': search_query,
        'total_users': users.count(),
    }

    return render(request, 'people/person_list.html', context)


def person_detail(request, user_id):
    """
    Display detailed information about a specific user.
    """
    user = get_object_or_404(User, id=user_id, is_active=True)

    context = {
        'contact_user': user,
    }

    return render(request, 'people/person_detail.html', context)
