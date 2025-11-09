from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from django_messaging.models import ChatRoom, ChatMembership, Message


class Command(BaseCommand):
    help = "Create demo users and conversations for screenshots"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing demo data before creating new data",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing demo data...")
            User.objects.filter(
                username__in=[
                    "emma.wilson",
                    "leo.martinez",
                    "maya.patel",
                    "ethan.chen",
                    "sofia.rodriguez",
                    "noah.thompson",
                    "lena.kim",
                    "ravi.sharma",
                ]
            ).delete()

        users_data = [
            {"first_name": "Emma", "last_name": "Wilson"},
            {"first_name": "Leo", "last_name": "Martinez"},
            {"first_name": "Maya", "last_name": "Patel"},
            {"first_name": "Ethan", "last_name": "Chen"},
            {"first_name": "Sofia", "last_name": "Rodriguez"},
            {"first_name": "Noah", "last_name": "Thompson"},
            {"first_name": "Lena", "last_name": "Kim"},
            {"first_name": "Ravi", "last_name": "Sharma"},
        ]

        users = {}
        for user_data in users_data:
            username = (
                f"{user_data['first_name'].lower()}.{user_data['last_name'].lower()}"
            )
            email = f"{username}@example.com"

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                    "email": email,
                    "is_active": True,
                },
            )
            if created:
                user.set_password("pass123")
                user.save()
                self.stdout.write(f"Created user: {username}")

            users[user_data["first_name"].lower()] = user

        base_time = timezone.now() - timedelta(hours=2)

        existing_chat1 = ChatRoom.objects.filter(
            is_group=False,
            is_room=False,
            content_type=None,
            object_id=None,
            members__in=[users["emma"], users["leo"]],
        ).distinct().first()

        if existing_chat1 and existing_chat1.members.count() == 2:
            chat1 = existing_chat1
            created = False
        else:
            chat1 = ChatRoom.objects.create(
                title="", is_group=False, is_room=False
            )
            ChatMembership.objects.create(
                chat=chat1, user=users["emma"], role=ChatMembership.Role.ADMIN
            )
            ChatMembership.objects.create(
                chat=chat1, user=users["leo"], role=ChatMembership.Role.MEMBER
            )
            created = True

            messages_1 = [
                (
                    users["emma"],
                    "Morning, Leo! I checked the client dashboard — looks like we're getting a lot of new signups this week. Did we launch the promo campaign already?",
                    0,
                ),
                (
                    users["leo"],
                    "Hey Emma! Yep, it went live on Tuesday. The click-through rate is higher than expected. Marketing did a great job tweaking the landing page copy.",
                    2,
                ),
                (
                    users["emma"],
                    "Nice! We should probably update the pricing FAQ before more people ask about the new plan tiers. Want me to draft it?",
                    5,
                ),
                (
                    users["leo"],
                    "That'd be perfect. I'll handle the visuals and make sure the design matches our new branding style.",
                    7,
                ),
                (
                    users["emma"],
                    "Great, I'll send you the doc by this afternoon. Maybe we can review it together tomorrow morning?",
                    10,
                ),
                (
                    users["leo"],
                    "Works for me. Let's grab coffee during the review — might as well turn it into a mini strategy session.",
                    12,
                ),
            ]

            for sender, content, minutes_offset in messages_1:
                msg = Message.objects.create(
                    chat=chat1,
                    sender=sender,
                    content=content,
                )
                msg.created_at = base_time + timedelta(minutes=minutes_offset)
                msg.save(update_fields=["created_at"])

            self.stdout.write("Created conversation 1: Emma and Leo")

        existing_chat2 = ChatRoom.objects.filter(
            title="Team Beta", is_group=True, is_room=False
        ).first()

        if existing_chat2:
            chat2 = existing_chat2
            created = False
        else:
            chat2 = ChatRoom.objects.create(
                title="Team Beta", is_group=True, is_room=False
            )
            ChatMembership.objects.create(
                chat=chat2, user=users["maya"], role=ChatMembership.Role.ADMIN
            )
            ChatMembership.objects.create(
                chat=chat2, user=users["ethan"], role=ChatMembership.Role.MEMBER
            )
            ChatMembership.objects.create(
                chat=chat2, user=users["sofia"], role=ChatMembership.Role.MEMBER
            )
            created = True

            messages_2 = [
                (
                    users["maya"],
                    "Morning, team! The beta users are loving the new dashboard layout — just got some great feedback on Slack.",
                    0,
                ),
                (
                    users["ethan"],
                    "That's awesome! Did anyone mention the loading speed? I tweaked the caching logic last night.",
                    3,
                ),
                (
                    users["sofia"],
                    "Yes, actually! One tester said it feels way faster now. Maya, are we ready to roll this out to all users next week?",
                    6,
                ),
                (
                    users["maya"],
                    "Almost. I just want to finalize the onboarding walkthrough first. It still feels a bit too wordy.",
                    9,
                ),
                (
                    users["ethan"],
                    "I can help with that. Maybe we replace some of the text with quick tooltips instead?",
                    11,
                ),
                (
                    users["sofia"],
                    "Good call. Let's meet tomorrow to polish it — same time as usual?",
                    13,
                ),
                (users["maya"], "Works for me. Let's make this release shine!", 15),
            ]

            for sender, content, minutes_offset in messages_2:
                msg = Message.objects.create(
                    chat=chat2,
                    sender=sender,
                    content=content,
                )
                msg.created_at = base_time + timedelta(minutes=minutes_offset)
                msg.save(update_fields=["created_at"])

            self.stdout.write("Created conversation 2: Maya, Ethan, and Sofia")

        from demo_project.apps.videos.models import Video
        from django.contrib.contenttypes.models import ContentType

        video, video_created = Video.objects.get_or_create(
            title="New Training Video",
            defaults={
                "description": "Training video for new workflow",
                "url": "https://www.youtube.com/watch?v=F5mRW0jo-U4",
                "embed_url": "https://www.youtube.com/embed/F5mRW0jo-U4",
                "thumbnail": "https://img.youtube.com/vi/F5mRW0jo-U4/maxresdefault.jpg",
                "uploaded_by": users["maya"],
            },
        )

        if video_created:
            self.stdout.write(f"Created video: {video.title}")

        content_type = ContentType.objects.get_for_model(Video)
        chat3, created = ChatRoom.objects.get_or_create(
            content_type=content_type,
            object_id=video.pk,
            defaults={
                "title": f"Discussion: {video.title}",
                "is_room": True,
                "is_group": True,
            },
        )

        if created:
            ChatMembership.objects.create(
                chat=chat3, user=users["noah"], role=ChatMembership.Role.MEMBER
            )
            ChatMembership.objects.create(
                chat=chat3, user=users["lena"], role=ChatMembership.Role.MEMBER
            )
            ChatMembership.objects.create(
                chat=chat3, user=users["ravi"], role=ChatMembership.Role.MEMBER
            )

            messages_3 = [
                (
                    users["noah"],
                    "Just finished watching the new training video — really liked how it breaks down the workflow step by step. Felt much clearer than the last one.",
                    0,
                ),
                (
                    users["lena"],
                    "Agreed! The visuals actually made it click for me. Though I think the audio volume could be balanced better — the narrator's voice dips a bit halfway through.",
                    4,
                ),
                (
                    users["ravi"],
                    "True, but overall it's solid. I especially liked the short recap at the end; makes it easier to remember the key actions.",
                    7,
                ),
                (
                    users["noah"],
                    "Yeah, that recap part was a smart move. Maybe we can add subtitles next time? Some people prefer reading along.",
                    10,
                ),
                (
                    users["lena"],
                    "Definitely. And maybe a quick quiz after the video? It'd help reinforce what everyone learned.",
                    13,
                ),
                (
                    users["ravi"],
                    "Great ideas. I'll pass that feedback to the training team — they'll be happy to hear this one actually landed well.",
                    16,
                ),
            ]

            for sender, content, minutes_offset in messages_3:
                msg = Message.objects.create(
                    chat=chat3,
                    sender=sender,
                    content=content,
                )
                msg.created_at = base_time + timedelta(minutes=minutes_offset)
                msg.save(update_fields=["created_at"])

            self.stdout.write(
                "Created conversation 3: Noah, Lena, and Ravi (video room)"
            )

        self.stdout.write(
            self.style.SUCCESS("Successfully created demo data for screenshots!")
        )
