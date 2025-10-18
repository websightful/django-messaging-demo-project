from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
import random

from demo_project.apps.videos.models import Video
from django_messaging.models import ChatRoom, ChatMembership


class Command(BaseCommand):
    help = 'Create sample videos and chat rooms for demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sample videos before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing sample videos...')
            Video.objects.all().delete()
            # Clear chat rooms that are attached to videos
            video_ct = ContentType.objects.get_for_model(Video)
            ChatRoom.objects.filter(content_type=video_ct).delete()

        # Get or create sample users
        users = []
        for i in range(5):
            username = f'user{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': f'User',
                    'last_name': f'{i+1}',
                    'email': f'{username}@example.com',
                    'is_active': True,
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'Created user: {username}')
            users.append(user)

        # Create sample videos
        video_data = [
            {
                'title': 'Introduction to Django',
                'description': 'Learn the basics of Django web framework in this comprehensive tutorial. Perfect for beginners who want to understand how to build web applications with Django.',
                'url': 'https://www.youtube.com/watch?v=F5mRW0jo-U4',
                'embed_url': 'https://www.youtube.com/embed/F5mRW0jo-U4',
                'thumbnail': 'https://img.youtube.com/vi/F5mRW0jo-U4/maxresdefault.jpg',
            },
            {
                'title': 'Python for Beginners',
                'description': 'A complete guide to getting started with Python programming. Covers variables, functions, loops, and object-oriented programming concepts.',
                'url': 'https://www.youtube.com/watch?v=kqtD5dpn9C8',
                'embed_url': 'https://www.youtube.com/embed/kqtD5dpn9C8',
                'thumbnail': 'https://img.youtube.com/vi/kqtD5dpn9C8/maxresdefault.jpg',
            },
            {
                'title': 'Web Development Best Practices',
                'description': 'Essential tips and tricks for modern web development. Learn about code organization, security, performance optimization, and maintainable code.',
                'url': 'https://www.youtube.com/watch?v=rWM2N26cq7s',
                'embed_url': 'https://www.youtube.com/embed/rWM2N26cq7s',
                'thumbnail': 'https://img.youtube.com/vi/rWM2N26cq7s/maxresdefault.jpg',
            },
            {
                'title': 'Django REST Framework Tutorial',
                'description': 'Build powerful APIs with Django REST Framework. Learn serializers, viewsets, authentication, and API documentation.',
                'url': 'https://www.youtube.com/watch?v=c708Nf0cHrs',
                'embed_url': 'https://www.youtube.com/embed/c708Nf0cHrs',
                'thumbnail': 'https://img.youtube.com/vi/c708Nf0cHrs/maxresdefault.jpg',
            },
            {
                'title': 'Frontend Development with React',
                'description': 'Modern frontend development using React. Covers components, state management, hooks, and integration with backend APIs.',
                'url': 'https://www.youtube.com/watch?v=Ke90Tje7VS0',
                'embed_url': 'https://www.youtube.com/embed/Ke90Tje7VS0',
                'thumbnail': 'https://img.youtube.com/vi/Ke90Tje7VS0/maxresdefault.jpg',
            },
            {
                'title': 'Database Design Fundamentals',
                'description': 'Learn the principles of good database design. Covers normalization, relationships, indexing, and query optimization.',
                'url': 'https://www.youtube.com/watch?v=ztHopE5Wnpc',
                'embed_url': 'https://www.youtube.com/embed/ztHopE5Wnpc',
                'thumbnail': 'https://img.youtube.com/vi/ztHopE5Wnpc/maxresdefault.jpg',
            },
        ]

        for video_info in video_data:
            video, created = Video.objects.get_or_create(
                title=video_info['title'],
                defaults={
                    **video_info,
                    'uploaded_by': random.choice(users),
                }
            )
            if created:
                self.stdout.write(f'Created video: {video.title}')
                
                # Create chat room for video
                content_type = ContentType.objects.get_for_model(Video)
                room, room_created = ChatRoom.objects.get_or_create(
                    content_type=content_type,
                    object_id=video.pk,
                    defaults={
                        'title': f"Discussion: {video.title}",
                        'is_room': True,
                        'is_group': True,
                    }
                )
                if room_created:
                    # Add some users to the room
                    user_count = min(random.randint(2, 4), len(users))
                    for user in random.sample(users, user_count):
                        ChatMembership.objects.get_or_create(
                            chat=room,
                            user=user,
                            defaults={'role': ChatMembership.Role.MEMBER}
                        )
                    self.stdout.write(f'Created chat room for video: {video.title}')

        # Create some standalone chat rooms for video discussions
        standalone_rooms = [
            {'title': 'Video Recommendations', 'description': 'Share and discuss great educational videos'},
            {'title': 'Learning Discussion', 'description': 'Discuss what you\'ve learned from videos'},
            {'title': 'Tech Tutorials', 'description': 'Chat about programming and development tutorials'},
        ]

        for room_info in standalone_rooms:
            room, created = ChatRoom.objects.get_or_create(
                title=room_info['title'],
                is_room=True,
                content_type=None,
                object_id=None,
                defaults={
                    'is_group': True,
                }
            )
            if created:
                self.stdout.write(f'Created standalone room: {room.title}')
                
                # Add some users to the room
                room_user_count = min(random.randint(2, 5), len(users))
                for user in random.sample(users, room_user_count):
                    ChatMembership.objects.get_or_create(
                        chat=room,
                        user=user,
                        defaults={'role': ChatMembership.Role.MEMBER}
                    )

        self.stdout.write(
            self.style.SUCCESS('Successfully created sample videos and chat rooms!')
        )
