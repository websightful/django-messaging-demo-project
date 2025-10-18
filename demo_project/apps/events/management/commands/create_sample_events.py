from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta
import random

from demo_project.apps.events.models import Event
from django_messaging.models import ChatRoom, ChatMembership


class Command(BaseCommand):
    help = 'Create sample events and chat rooms for demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing sample events before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing sample events...')
            Event.objects.all().delete()
            # Clear chat rooms that are attached to events
            event_ct = ContentType.objects.get_for_model(Event)
            ChatRoom.objects.filter(content_type=event_ct).delete()

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

        # Create sample events
        now = timezone.now()
        event_data = [
            {
                'title': 'Django Meetup',
                'description': 'Monthly Django developers meetup. Come learn and network with fellow Django enthusiasts! We\'ll have talks on the latest Django features, best practices, and networking opportunities.',
                'start_date': now + timedelta(days=7),
                'end_date': now + timedelta(days=7, hours=2),
                'location': 'Tech Hub, Downtown',
                'max_attendees': 50,
            },
            {
                'title': 'Python Workshop',
                'description': 'Hands-on Python programming workshop for beginners. Learn the fundamentals of Python programming through practical exercises and real-world examples.',
                'start_date': now + timedelta(days=14),
                'end_date': now + timedelta(days=14, hours=4),
                'location': 'Community Center',
                'max_attendees': 30,
            },
            {
                'title': 'Web Development Conference',
                'description': 'Annual conference featuring the latest in web development. Join industry experts as they share insights on modern web technologies, frameworks, and development practices.',
                'start_date': now + timedelta(days=30),
                'end_date': now + timedelta(days=32),
                'location': 'Convention Center',
                'max_attendees': 200,
            },
            {
                'title': 'React & Django Integration Workshop',
                'description': 'Learn how to build modern web applications by combining React frontend with Django backend. Perfect for full-stack developers.',
                'start_date': now + timedelta(days=21),
                'end_date': now + timedelta(days=21, hours=6),
                'location': 'Innovation Lab',
                'max_attendees': 25,
            },
            {
                'title': 'Open Source Contribution Day',
                'description': 'Join us for a day of contributing to open source projects. Great for beginners and experienced developers alike.',
                'start_date': now + timedelta(days=45),
                'end_date': now + timedelta(days=45, hours=8),
                'location': 'Co-working Space',
                'max_attendees': 40,
            },
        ]

        for event_info in event_data:
            event, created = Event.objects.get_or_create(
                title=event_info['title'],
                defaults={
                    **event_info,
                    'organizer': random.choice(users),
                }
            )
            if created:
                self.stdout.write(f'Created event: {event.title}')
                
                # Create chat room for event
                content_type = ContentType.objects.get_for_model(Event)
                room, room_created = ChatRoom.objects.get_or_create(
                    content_type=content_type,
                    object_id=event.pk,
                    defaults={
                        'title': f"Discussion: {event.title}",
                        'is_room': True,
                        'is_group': True,
                    }
                )
                if room_created:
                    # Add some random users to the room
                    room_member_count = min(random.randint(2, 4), len(users))
                    for user in random.sample(users, room_member_count):
                        ChatMembership.objects.get_or_create(
                            chat=room,
                            user=user,
                            defaults={'role': ChatMembership.Role.MEMBER}
                        )
                    self.stdout.write(f'Created chat room for event: {event.title}')

        # Create some standalone chat rooms for event community
        standalone_rooms = [
            {'title': 'Event Planning', 'description': 'Discuss upcoming events and ideas'},
            {'title': 'Tech Networking', 'description': 'Connect with other tech professionals'},
            {'title': 'General Discussion', 'description': 'General chat for all community members'},
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
            self.style.SUCCESS('Successfully created sample events and chat rooms!')
        )
